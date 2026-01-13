from transcription import transcribe_audio
import asyncio
import json
import aiohttp
import re
from collections import Counter
from flask import Response
from flask import jsonify
from flask import request
from flask import render_template
from flask import session
from flask import url_for
from flask import redirect
import requests
from flask_sqlalchemy import SQLAlchemy


app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)


NEURO_API_URL = "http://127.0.0.1:5000/neuro_api"


def send_request_to_api(payload):
    print("Отправка запроса к API с payload:", payload)
    response = requests.post(NEURO_API_URL, json=payload)
    if response.status_code == 200:
        print("API response:", response.json())
        return response.json()
    else:
        print("Ошибка API:", response.text)
        return {"error": "API Error", "details": response.text}


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    user_info = db.Column(db.JSON, default={})
    course_info = db.Column(MutableList.as_mutable(db.JSON), default=[])
    has_completed_interview = db.Column(db.Boolean, default=False)


def require_login():
    if 'user_id' not in session:
        return redirect(url_for('register'))
    user = User.query.get(session['user_id'])
    if not user.user_info:
        return redirect(url_for('interview'))
    return user


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
        "5_categories": [],
        "6_teaching_style": "",
        "7_lecture_type": ""
    }


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


class PublicCourse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    creator = db.Column(db.String(80), nullable=False)
    course_info = db.Column(db.JSON, nullable=False)
    rating = db.Column(db.Float, default=10.0)


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


def library():
    user = require_login()
    if isinstance(user, Response):
        return user

    if not user.course_info:
        user.course_info = []

    print("Текущее состояние course_info пользователя:", user.course_info)

    courses_with_indices = [{"index": idx, "course": course} for idx, course in enumerate(user.course_info)]
    print("Курсы с индексами для шаблона:", courses_with_indices)

    categories = []
    for course_wrapper in user.course_info:
        categories.extend(course_wrapper["course"].get("5_categories", []))
    
    category_counts = Counter(categories)
    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)

    new_course_index = len(user.course_info)
    new_course_url = url_for('course_creation', user_id=user.id, course_idx=new_course_index)
    print('======================')
    print(user.username)
    return render_template(
        'library.html',
        user=user,
        courses_with_indices=courses_with_indices,
        new_course_url=new_course_url,
        sorted_categories=sorted_categories, 
        username=user.username
    )


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


def update_course_info(user_id, course_idx):
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('login'))
    
    course_name = request.form.get('course_name')
    learning_format = request.form.get('learning_format')
    lecture_type = request.form.get('lecture_type')
    
    course_info = user.course_info[course_idx]["course"]
    if course_name:
        course_info['3_name'] = course_name
    if learning_format:
        course_info['learning_format'] = learning_format
    if lecture_type:
        course_info['lecture_type'] = lecture_type
    
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


def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return redirect(url_for('library'))  
    return redirect(url_for('login'))


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


def account():
    user = require_login()
    if isinstance(user, Response):
        return user
    user = User.query.get(session['user_id'])
    message = ""
    if request.method == 'POST':
        new_username = request.form.get('username')
        new_password = request.form.get('password')
        
        if new_username and new_username != user.username:
            existing = User.query.filter(User.username == new_username, User.id != user.id).first()
            if existing:
                message = "Username already taken."
            else:
                user.username = new_username
                message = "Username updated successfully."
        if new_password:
            user.password = new_password
            message += " Password updated successfully."
        db.session.commit()
    
    def clean_key(key):
        cleaned = re.sub(r'\d+', '', key).replace('_', ' ').strip()
        return cleaned.capitalize()
    interview_results = []
    if isinstance(user.user_info, dict):
        for key, value in user.user_info.items():
            interview_results.append((clean_key(key), value))
    return render_template('account.html', user=user, message=message, interview_results=interview_results)


def interview():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        conversation_text = request.form['conversation']
        conversation = session.get('conversation', [])
        conversation.append({"role": "user", "content": conversation_text})

        payload = {
            "0_content": {
                "0_conversation": conversation,
                "1_user_info": user.user_info
            },
            "1_type": "interview"
        }
        response = send_request_to_api(payload)

        if response.get("response"):
            conversation.append({"role": "manager", "content": response["response"]})

        session['conversation'] = conversation

        if response.get("user_info"):
            print("Обновление user_info в базе данных")
            user.user_info = response["user_info"]
            if "<END>" in response.get("status"):
                user.has_completed_interview = True
            db.session.commit()

        return jsonify(response)

    session['conversation'] = []  
    return render_template('interview.html', username=user.username)


def course_edit(user_id, course_idx):
    user = require_login()
    if isinstance(user, Response):
        return user
    user = User.query.get(user_id)
    if not user or user.id != session['user_id']:
        return "Доступ запрещен", 403

    if request.method == 'POST':
        print(f"Начинаем редактирование курса для user_id={user_id}, course_idx={course_idx}")
        conversation_text = request.form['conversation']
        conversation = session.get('conversation', [])
        conversation.append({"role": "user", "content": conversation_text})

        if len(user.course_info) <= course_idx:
            return "Курс с указанным индексом не найден.", 404

        course_info = user.course_info[course_idx]["course"]

        print("Текущее course_info для редактирования:", course_info)

        payload = {
            "0_content": {
                "0_conversation": conversation,
                "1_user_info": user.user_info,
                "2_course_info": course_info
            },
            "1_type": "course_edit"
        }
        response = send_request_to_api(payload)

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
    return render_template('course_edit.html', user=user, course_idx=course_idx, username=user.username, course_name = user.course_info[course_idx]["course"]["3_name"])


def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))


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


with app.app_context():
    db.create_all()


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


if __name__ == '__main__':
    app.run(port=8000, debug=True)


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


NEURO_REALTIME_API_URL = "http://127.0.0.1:5000/neuro_realtime_api"


async def send_request_to_realtime_api(payload):
    async with aiohttp.ClientSession() as session:
        async with session.post(NEURO_REALTIME_API_URL, json=payload) as response:
            
            async for line in response.content:
                try:
                    piece = json.loads(line.decode('utf-8').strip())
                    yield piece
                except Exception as e:
                    print("Error decoding piece:", e)


audio_queues = {}


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
