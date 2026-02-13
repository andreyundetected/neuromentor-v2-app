import asyncio
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, Response, stream_with_context
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.mutable import MutableList
import requests
import re
from transcription import transcribe_audio
import aiohttp
import json
from collections import Counter

app = Flask(__name__)
app.secret_key = 'supersecretkey'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///neuromentor.db'


db = SQLAlchemy(app)

NEURO_API_URL = "http://127.0.0.1:5000/neuro_api"


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    user_info = db.Column(db.JSON, default={})
    course_info = db.Column(MutableList.as_mutable(db.JSON), default=[])
    has_completed_interview = db.Column(db.Boolean, default=False)

class PublicCourse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    creator = db.Column(db.String(80), nullable=False)
    course_info = db.Column(db.JSON, nullable=False)
    rating = db.Column(db.Float, default=10.0)

with app.app_context():
    db.create_all()

def send_request_to_api(payload):
    print("Отправка запроса к API с payload:", payload)
    response = requests.post(NEURO_API_URL, json=payload)
    if response.status_code == 200:
        print("API response:", response.json())
        return response.json()
    else:
        print("Ошибка API:", response.text)
        return {"error": "API Error", "details": response.text}

async def send_request_to_realtime_api(payload):
    async with aiohttp.ClientSession() as session:
        async with session.post(NEURO_REALTIME_API_URL, json=payload) as response:
            
            async for line in response.content:
                try:
                    piece = json.loads(line.decode('utf-8').strip())
                    yield piece
                except Exception as e:
                    print("Error decoding piece:", e)

def get_empty_course_info():
    return {
        "0_topic": "",
        "1_initial_level": "",
        "2_target_level": "",
        "3_name": "",
        "4_structure": [
            {
                "0_topic": "",
                "1_description": "",
                "2_instructions_for_generating_lessons": "",
                "3_lessons": [
                    {"name": "", "description": ""},
                    {"name": "", "description": ""}
                ]
            }
        ],
        "5_categories": []
    }

def require_login():
    if 'user_id' not in session:
        return redirect(url_for('register'))
    user = User.query.get(session['user_id'])
    if not user.user_info:
        return redirect(url_for('interview'))
    return user

@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return redirect(url_for('library'))  
    return redirect(url_for('login'))  

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            return "Неверное имя пользователя или пароль"

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            return "Пользователь уже существует"

        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')


@app.route('/interview', methods=['GET', 'POST'])


@app.route('/add_to_library/<int:course_id>', methods=['POST'])
def add_to_library(course_id):
    user = require_login()
    if isinstance(user, Response):
        return user

    public_course = PublicCourse.query.get(course_id)
    if not public_course:
        return "Курс не найден.", 404

    if any(c.get('id') == course_id for c in user.course_info):
        return redirect(url_for('library'))  

    updated_course_info = user.course_info + [{
        **public_course.course_info,
        "id": course_id  
    }]
    
    User.query.filter_by(id=user.id).update({"course_info": updated_course_info})
    db.session.commit()

    return redirect(url_for('library'))

@app.route('/delete_course/<int:course_idx>', methods=['POST'])
def delete_course(course_idx):
    user = require_login()
    if isinstance(user, Response):
        return user
    user = User.query.get(session['user_id'])
    if course_idx < 0 or course_idx >= len(user.course_info):
        return "Course not found", 404
    user.course_info.pop(course_idx)
    db.session.commit()
    return redirect(url_for('library'))

@app.route('/update_course/<int:course_id>', methods=['POST'])
def update_course(course_id):
    user = require_login()
    if isinstance(user, Response):
        return user

    course_to_update = PublicCourse.query.filter_by(id=course_id, creator=user.username).first()
    if not course_to_update:
        return "Курс не найден или вы не являетесь его владельцем.", 403

    new_name = request.form.get('course_name')
    new_topic = request.form.get('course_topic')

    if new_name:
        course_to_update.name = new_name
    if new_topic:
        course_to_update.topic = new_topic

    db.session.commit()

    return redirect(url_for('index'))

@app.route('/library')


@app.route('/account', methods=['GET', 'POST'])


@app.route('/course_creation/<int:user_id>/<int:course_idx>', methods=['GET', 'POST'])
def course_creation(user_id, course_idx):
    user = require_login()
    if isinstance(user, Response):
        return user
    user = User.query.get(user_id)
    if not user or user.id != session['user_id']:
        return "Доступ запрещен", 403

    if request.method == 'POST':
        print(f"Начинаем обработку генерации курса для user_id={user_id}, course_idx={course_idx}")
        conversation_text = request.form['conversation']
        conversation = session.get('conversation', [])
        conversation.append({"role": "user", "content": conversation_text})

        if not user.course_info:
            user.course_info = []

        while len(user.course_info) <= course_idx:
            user.course_info.append({
                "course": get_empty_course_info(),
                "course_settings": {}
            })

        course_info = user.course_info[course_idx]["course"]

        print("Текущее course_info:", course_info)

        payload = {
            "0_content": {
                "0_conversation": conversation,
                "1_user_info": user.user_info,
                "2_course_info": course_info
            },
            "1_type": "course_creation"
        }
        response = send_request_to_api(payload)

        if "<END>" in response.get("status"):
            first_lesson = user.course_info[course_idx]["course"]["4_structure"][0]["3_lessons"][0]["name"]
            user.course_info[course_idx]["course_settings"] = {"lesson": first_lesson}
            User.query.filter_by(id=user.id).update({"course_info": user.course_info})
            db.session.commit()

        if response.get("response"):
            conversation.append({"role": "manager", "content": response["response"]})

        session['conversation'] = conversation

        if "course_info" in response:
            print(f"Обновление course_info для индекса {course_idx}")
            user.course_info[course_idx]["course"] = response["course_info"]
            print(f"Новое course_info: {user.course_info[course_idx]['course']}")

        try:
            
            User.query.filter_by(id=user.id).update({"course_info": user.course_info})
            db.session.commit()  
            print("Изменения успешно сохранены в базе данных.")
        except Exception as e:
            print("Ошибка при сохранении в базе данных:", e)

        return jsonify(response)

    session['conversation'] = []  

    try:
        course_name = user.course_info[course_idx]["course"]["3_name"]
    except:
        course_name = ""
    return render_template('course_creation.html', user=user, course_idx=course_idx, username=user.username, course_name = course_name)

@app.route('/public_course/<int:course_id>', methods=['GET', 'POST'])
def public_course_view(course_id):
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])

    public_course = PublicCourse.query.get(course_id)
    if not public_course:
        return "Курс не найден", 404

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_to_library':
            return redirect(url_for('add_to_library', course_id=course_id))
        elif action == 'trial_lesson':
            
            return redirect(url_for('lesson', user_id=user.id, course_idx=0))

    return render_template(
        'public_course.html',
        user=user,
        course=public_course
    )

@app.route('/course_edit/<int:user_id>/<int:course_idx>', methods=['GET', 'POST'])


@app.route('/course_select/<int:user_id>/<int:course_idx>', methods=['GET', 'POST'])
def course_select(user_id, course_idx):
    user = require_login()
    if isinstance(user, Response):
        return user
    user = User.query.get(user_id)
    if not user or user.id != session['user_id']:
        return "Доступ запрещен", 403

    if not user or course_idx >= len(user.course_info):
        return "Курс не найден", 404

    course = user.course_info[course_idx]["course"]  

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'lesson':
            return redirect(url_for('lesson_call', user_id=user_id, course_idx=course_idx))
        elif action == 'edit':
            return redirect(url_for('course_edit', user_id=user_id, course_idx=course_idx))
        elif action == 'settings':
            return redirect(url_for('course_settings', user_id=user_id, course_idx=course_idx))
    
    progress_count = 0
    count = 0
    flag = False
    for big_topic in user.course_info[course_idx]["course"]["4_structure"]:
        count += len(big_topic["3_lessons"])
        for topic in big_topic["3_lessons"]:
            print(user.course_info[course_idx]["course_settings"]["lesson"])
            print(topic)
            if topic["name"] == user.course_info[course_idx]["course_settings"]["lesson"]:
                flag = True
            if flag == False:
                progress_count += 1
    
    progress = int(progress_count / count * 10000)/100
    User.query.filter_by(id=user.id).update({"course_info": user.course_info})
    
    return render_template('course_select.html', user=user, course=course, course_idx=course_idx, username=user.username, progress = progress, course_id = course_idx)

@app.route('/course_select/<int:user_id>/<int:course_idx>/lesson_chat', methods=['GET', 'POST'])
def lesson_chat(user_id, course_idx):
    user = require_login()
    if isinstance(user, Response):
        return user
    user = User.query.get(user_id)
    if not user or user.id != session['user_id']:
        return "Доступ запрещен", 403

    if request.method == 'POST':
        
        conversation_text = request.form['conversation']
        conversation = session.get('conversation', [])
        progress = session.get('progress', 0)
        conversation.append({"role": "user", "content": conversation_text})

        if len(user.course_info) <= course_idx:
            return "Курс с указанным индексом не найден.", 404
        
        user_course_info = user.course_info[course_idx]
        if not user.course_info[course_idx]["course_settings"].get("lesson"):
            print("0000000000000000000")
            print(user.course_info[course_idx]["course_settings"].get("lesson"))
            user.course_info[course_idx]["course_settings"]["lesson"] = user.course_info[course_idx]["course"]["4_structure"][0]["3_lessons"][0]["name"]
            User.query.filter_by(id=user.id).update({"course_info": user.course_info})
            db.session.commit()
        lesson_topic = user.course_info[course_idx]["course_settings"].get("lesson")

        payload = {
            "0_content": {
                "0_conversation": conversation,
                "1_user_info": user.user_info,
                "2_user_course_info": user_course_info,
                "3_course_info": user.course_info[course_idx]["course"],
                "4_lesson_topic": lesson_topic,
                "5_progress": progress
            },
            "1_type": "lesson"
        }
        response = send_request_to_api(payload)
        print("0=0=0=0=0=0=0==0=0=0=0=0=0")
        if "<END>" in response.get("status"):
            flag = False
            stop_all = False  
            for big_topic in user.course_info[course_idx]["course"]["4_structure"]:
                if stop_all:  
                    break
                for topic in big_topic["3_lessons"]:
                    print("LESSON: ")
                    print(user.course_info[course_idx]["course_settings"]["lesson"])
                    print("TOPIC NAME: ")
                    print(topic["name"])
                    if flag:
                        user.course_info[course_idx]["course_settings"]["lesson"] = topic["name"]
                        print("LESSON: ")
                        print(user.course_info[course_idx]["course_settings"]["lesson"])
                        print("TOPIC NAME: ")
                        print(topic["name"])
                        print("TOPIC: ")
                        print(topic)
                        stop_all = True  
                        break  
                    if topic["name"] == user.course_info[course_idx]["course_settings"]["lesson"]:
                        flag = True
                        
            print(user.course_info[course_idx]["course_settings"]["lesson"])
            User.query.filter_by(id=user.id).update({"course_info": user.course_info})
            db.session.commit()

        if response.get("response"):
            status = response.get('status')
            conversation.append({"role": f"teacher {status}", "content": response["response"]})

        session['conversation'] = conversation
        return jsonify(response)

    session['conversation'] = []  
    progress = 0
    return render_template('lesson_chat.html', user=user, course_idx=course_idx, username=user.username, lesson_title = user.course_info[course_idx]["course_settings"]["lesson"])



def event_stream(user_id, course_idx):
    queue = asyncio.Queue()
    audio_queues[(user_id, course_idx)] = queue  

    while True:
        audio_chunk = asyncio.run(queue.get())  
        print("in event_stream")
        yield f"data: {json.dumps({'audio': audio_chunk})}\n\n"

@app.route('/stream_audio/<int:user_id>/<int:course_idx>')
def stream_audio(user_id, course_idx):
    print("in stream_audio")
    return Response(stream_with_context(event_stream(user_id, course_idx)), content_type="text/event-stream")

@app.route('/course_select/<int:user_id>/<int:course_idx>/lesson_call', methods=['GET', 'POST'])
def lesson_call(user_id, course_idx):
    user = require_login()
    if isinstance(user, Response):
        return user
    user = User.query.get(user_id)
    if not user or user.id != session['user_id']:
        return "Access Denied", 403

    if request.method == 'POST':
        print("[LESSON_CALL] request.form:", request.form)
        print("[LESSON_CALL] request.files:", request.files)
        conversation_text = request.form.get('conversation', '')
        conversation = session.get('conversation', [])
        progress = session.get('progress', 0)

        if conversation_text:
            conversation.append({"role": "user", "content": conversation_text})
        
        audio_file = request.files.get('audio')
        if audio_file:
            try:
                transcript_result = transcribe().get_json()["transcript"]
                print("[LESSON_CALL] Transcription from audio:", transcript_result)
                conversation.append({"role": "user_audio", "content": transcript_result})
            except Exception as e:
                print("[LESSON_CALL] Error transcribing audio:", e)
        
        if len(user.course_info) <= course_idx:
            return "Course not found", 404

        user_course_info = user.course_info[course_idx]
        if not user.course_info[course_idx]["course_settings"].get("lesson"):
            user.course_info[course_idx]["course_settings"]["lesson"] =                user.course_info[course_idx]["course"]["4_structure"][0]["3_lessons"][0]["name"]
            User.query.filter_by(id=user.id).update({"course_info": user.course_info})
            db.session.commit()
        lesson_topic = user.course_info[course_idx]["course_settings"].get("lesson")

        payload = {
            "0_content": {
                "0_conversation": conversation,
                "1_user_info": user.user_info,
                "2_user_course_info": user_course_info,
                "3_course_info": user.course_info[course_idx]["course"],
                "4_lesson_topic": lesson_topic,
                "5_progress": progress,
                
            },
            "1_type": "lesson_call"
        }
        print("============================")
        print(conversation)
        transcript_list = []

        async def process_realtime():
            teacher_response = ""
            
            async for piece in send_request_to_realtime_api(payload):
                resp = piece.get("response", {})
                resp_type = piece.get("type")
                if resp_type == "text":
                    content = piece.get("content", "")
                    teacher_response += content
                    transcript_list.append(content)
                    print("[REALTIME] Received text piece:", content)
                elif resp_type == "audio":
                    print("[REALTIME] Received audio piece")
                    if (user_id, course_idx) in audio_queues:
                        print(f"{user_id}  {course_idx} in audio_queues")
                        await audio_queues[(user_id, course_idx)].put(content)  

                elif resp_type == "done":
                    print("[REALTIME] Received done signal")
                    conversation.append({"role": "teacher", "content": teacher_response})
                    break

        try:
            asyncio.run(process_realtime())
        except Exception as e:
            raise(e)
            print("[LESSON_CALL] Error during realtime processing:", e)
            return jsonify({"error": "Realtime processing failed"}), 500

        User.query.filter_by(id=user.id).update({"course_info": user.course_info})
        db.session.commit()
        session['conversation'] = conversation
        return jsonify({"status": "<END>", "response": "".join(transcript_list)})

    session['conversation'] = []
    progress = 0
    lesson_title = user.course_info[course_idx]["course_settings"].get("lesson", "")
    return render_template('lesson_call.html', user=user, course_idx=course_idx, username=user.username, lesson_title=lesson_title)

@app.route('/transcribe', methods=['POST'])
def transcribe():
    print("[TRANSCRIBE] Endpoint called")
    if 'audio' not in request.files:
        print("[TRANSCRIBE] No audio file provided")
        return jsonify({"error": "No audio file provided"}), 400
    audio_file = request.files['audio']
    print(f"[TRANSCRIBE] Audio content type: {audio_file.content_type}")
    audio_bytes = audio_file.read()
    print(f"[TRANSCRIBE] Received audio file of length: {len(audio_bytes)} bytes")
    
    with open("debug_received_audio", "wb") as f:
        f.write(audio_bytes)

    print("[TRANSCRIBE] First 64 bytes of received audio:", audio_bytes[:64])

    print(f"[TRANSCRIBE] Received audio file of length: {len(audio_bytes)} bytes")
    
    with open("debug_input.webm", "wb") as f:
        f.write(audio_bytes)
    print(f"[TRANSCRIBE] Saved raw audio as debug_input.webm")

    if audio_bytes.startswith(b'RIFF'):
        print("[TRANSCRIBE] Audio appears to be in WAV format.")
        wav_data = audio_bytes
    else:
        print("[TRANSCRIBE] Audio is not WAV, attempting conversion via ffmpeg...")
        import subprocess
        try:
            process = subprocess.run(
                ['ffmpeg', '-nostdin', '-y', '-f', 'webm', '-i', 'debug_input.webm', '-c:a', 'pcm_s16le', '-ar', '16000', '-ac', '1', 'debug_converted.wav'],
                capture_output=True,
                timeout=30
            )

        except subprocess.TimeoutExpired:
            print("[TRANSCRIBE] FFmpeg process timed out.")
            return jsonify({"error": "Conversion timed out"}), 500

        if process.returncode != 0:
            print("[TRANSCRIBE] FFmpeg error:", process.stderr.decode())
            return jsonify({"error": "Conversion failed"}), 500

        with open("debug_converted.wav", "rb") as f:
            wav_data = f.read()
        print("[TRANSCRIBE] Conversion successful, WAV data starts with RIFF:", wav_data.startswith(b'RIFF'))
    try:
        transcript = asyncio.run(transcribe_audio(wav_data))
        print(f"[TRANSCRIBE] Transcription result: {transcript}")
        return jsonify({"transcript": transcript})
    except Exception as e:
        print(f"[TRANSCRIBE] Error during transcription: {e}")
        return jsonify({"error": "Transcription failed"}), 500

@app.route('/update_course_info/<int:user_id>/<int:course_idx>', methods=['POST'])
def update_course_info(user_id, course_idx):
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('login'))
    
    course_name = request.form.get('course_name')
    learning_format = request.form.get('learning_format')
    
    course_info = user.course_info[course_idx]["course"]
    if course_name:
        course_info['3_name'] = course_name
    if learning_format:
        course_info['learning_format'] = learning_format
    
    if 'course_settings' not in session:
        session['course_settings'] = {}
    
    course_settings = session['course_settings'].get(course_idx, [])
    updated_lessons = []

    for topic in course_info['4_structure']:
        for lesson in topic['3_lessons']:
            
            lesson_name = lesson['name']
            lesson_status = next(
                (ls['completed'] for ls in course_settings if ls['name'] == lesson_name), 
                False
            )
            updated_lessons.append({'name': lesson_name, 'completed': lesson_status})
    
    session['course_settings'][course_idx] = updated_lessons
    
    db.session.commit()
    session.modified = True
    
    return redirect(url_for('course_settings', user_id=user.id, course_idx=course_idx))

@app.route('/course_settings/<int:user_id>/<int:course_idx>')
def course_settings(user_id, course_idx):
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('login'))
    
    course_info = user.course_info[course_idx]["course"]
    course_settings = session.get('course_settings', {}).get(course_idx, [])
    
    nearest_lesson = None
    for setting in course_settings:
        if not setting['completed']:
            nearest_lesson = setting['name']
            break
    
    return render_template(
        'course_settings.html',
        user=user,
        course_idx=course_idx,
        course_info=course_info,
        course_settings=course_settings,
        nearest_lesson=nearest_lesson
    )

if __name__ == '__main__':
    app.run(port=8000, debug=True)
