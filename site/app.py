from services.require_login import require_login
from quart import Quart, render_template, request, jsonify, session, Response, redirect, url_for
from tortoise import Tortoise, fields, connections
from tortoise.models import Model
import re
from transcription import transcribe_audio_with_prepare_data
import aiohttp
import json
import os
from models import init_db
from routes import blueprints
from models.user import User
from services.user_service import require_login
from collections import Counter

app = Quart(__name__)
app.secret_key = 'supersecretkey'

for bp in blueprints:
    app.register_blueprint(bp)

DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql://", "postgres://")

NEURO_API_URL = "https://" + os.getenv("NEURO_API-DOMAIN", "") + "/neuro_api"

class PublicCourse(Model):
    id = fields.BigIntField(pk=True)
    name = fields.CharField(max_length=100)
    topic = fields.CharField(max_length=100)
    creator = fields.CharField(max_length=80)
    course_info = fields.JSONField()
    rating = fields.FloatField(default=10.0)

@app.before_serving
async def startup():
    await init_db(DATABASE_URL)

@app.after_serving
async def shutdown():
    await Tortoise.close_connections()

async def send_request_to_api(payload):
    print("Отправка запроса к API с payload:", payload)
    async with aiohttp.ClientSession() as session:
        async with session.post(NEURO_API_URL, json=payload) as response:
            return await response.json()

async def get_empty_course_info():
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

@app.route('/')
async def index():
    if "user_id" in session:
        user = await User.get(id=session["user_id"])
        if user:
            session["language"] = user.user_info.get("language", "ru")
            return redirect(url_for("dashboard.library"))
    return redirect(url_for("auth.login"))

async def ensure_db_connection():
    if not connections._get_storage():
        await init_db()

@app.route('/api/check_interview_status')
async def check_interview_status():
    user = await require_login()
    if isinstance(user, Response):
        return jsonify({"has_completed_interview": False})
    
    return jsonify({"has_completed_interview": user.has_completed_interview})

@app.route('/interview', methods=['GET', 'POST'])
async def interview():
    if 'user_id' not in session:
        return redirect(url_for("auth.login"))

    user = await User.get(id=session['user_id'])

    if request.method == 'POST':
        form = await request.form
        conversation_text = form['conversation']
        conversation = session.get('conversation', [])
        conversation.append({"role": "user", "content": conversation_text})

        payload = {
            "0_content": {
                "0_conversation": conversation,
                "1_user_info": user.user_info
            },
            "1_type": "interview"
        }
        response = await send_request_to_api(payload)

        if response.get("response"):
            conversation.append({"role": "manager", "content": response["response"]})

        session['conversation'] = conversation

        if response.get("user_info"):
            print("Обновление user_info в базе данных")
            user.user_info = response["user_info"]
            if "<END>" in response.get("status"):
                user.has_completed_interview = True
            await user.save()

        return jsonify(response)

    session['conversation'] = []  
    return await render_template('interview.html', username=user.username)

@app.route('/start_recommendation/<int:recommendation_idx>', methods=['GET', 'POST'])
async def start_recommendation(recommendation_idx):
    user = await require_login()
    if isinstance(user, Response):
        return user

    if recommendation_idx >= len(user.recommendations):
        return "Recommendation not found", 404

    recommendation = user.recommendations[recommendation_idx]
    base_json = recommendation.get("base_json", {})
    start_message = recommendation.get("start_message", "Welcome to your recommended course!")

    if not user.course_info:
        user.course_info = []
    
    course_idx = len(user.course_info)
    user.course_info.append({"course": base_json, "course_settings": {}})
    await User.filter(id=user.id).update(course_info=user.course_info)

    return redirect(url_for('course.course_creation', user_id=user.id, course_idx=course_idx, start_message=start_message))

@app.route('/library')
async def library():
    user = await require_login()
    if isinstance(user, Response):
        return user

    if not user.recommendations or True:
        user.recommendations = generate_default_recommendations()
        await User.filter(id=user.id).update(recommendations=user.recommendations)
        
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
    return await render_template(
        'library.html',
        user=user,
        courses_with_indices=courses_with_indices,
        new_course_url=new_course_url,
        sorted_categories=sorted_categories, 
        username=user.username,
        enumerate=enumerate,
        show_interview_modal=not user.has_completed_interview
    )

@app.route('/account', methods=['GET', 'POST'])
async def account():
    user = await require_login()
    if isinstance(user, Response):
        return user
    user = await User.get(id=session['user_id'])

    message = ""
    if request.method == 'POST':
        form = await request.form
        new_username = form.get('username')
        new_password = form.get('password')
        
        if new_username and new_username != user.username:
            existing = await User.filter(username=new_username).exclude(id=user.id).first()

            if existing:
                message = "Username already taken."
            else:
                user.username = new_username
                message = "Username updated successfully."
        if new_password:
            user.password = new_password
            message += " Password updated successfully."
        
    async def clean_key(key):
        cleaned = re.sub(r'\d+', '', key).replace('_', ' ').strip()
        return cleaned.capitalize()
    interview_results = []
    if isinstance(user.user_info, dict):
        for key, value in user.user_info.items():
            interview_results.append((clean_key(key), value))
    return await render_template('account.html', user=user, message=message, interview_results=interview_results)

@app.route("/set_language/<lang>", methods=["POST"])
async def set_language(lang):

    if lang not in ["ru", "en"]:
        lang = "ru"

    user_id = session.get("user_id")
    if not user_id:
        return "Unauthorized", 401

    user = await User.get(id=user_id)

    if not user:
        return "User not found", 404

    user.user_info["language"] = lang
    await User.filter(id=user.id).update(user_info=user.user_info)

    session["language"] = lang

    return "", 204  

@app.route('/course_select/<int:user_id>/<int:course_idx>/lesson_chat', methods=['GET', 'POST'])
async def lesson_chat(user_id, course_idx):
    user = await require_login()
    if isinstance(user, Response):
        return user
    user = await User.get(id=user_id)

    if not user or user.id != session['user_id']:
        return "Доступ запрещен", 403

    if request.method == 'POST':
        form = await request.form
        
        conversation_text = form['conversation']
        conversation = session.get('conversation', [])
        progress = session.get('progress', 0)
        conversation.append({"role": "user", "content": conversation_text})

        if len(user.course_info) <= course_idx:
            return "Курс с указанным индексом не найден.", 404
        
        if not user.course_info[course_idx]["course_settings"].get("lesson"):
            print("0000000000000000000")
            print(user.course_info[course_idx]["course_settings"].get("lesson"))
            user.course_info[course_idx]["course_settings"]["lesson"] = user.course_info[course_idx]["course"]["4_structure"][0]["3_lessons"][0]["name"]
            await User.filter(id=user.id).update(course_info=user.course_info)
        lesson_topic = user.course_info[course_idx]["course_settings"].get("lesson")

        payload = {
            "0_content": {
                "0_conversation": conversation,
                "1_user_info": user.user_info,
                "2_course_info": user.course_info[course_idx]["course"],
                "3_lesson_topic": lesson_topic,
                "4_progress": progress
            },
            "1_type": "lesson"
        }
        response = await send_request_to_api(payload)
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
            await User.filter(id=user.id).update(course_info=user.course_info)

        if response.get("response"):
            response_type = response.get('response_type')
            conversation.append({"role": f"teacher {response_type}", "content": response["response"]})

        session['conversation'] = conversation
        return jsonify(response)

    session['conversation'] = []  
    progress = 0
    return await render_template('lesson_chat.html', user=user, course_idx=course_idx, username=user.username, lesson_title = user.course_info[course_idx]["course_settings"]["lesson"])

@app.route('/course_select/<int:user_id>/<int:course_idx>/lesson_call', methods=['GET', 'POST'])
async def lesson_call(user_id, course_idx):

    user = await require_login()
    if isinstance(user, Response):
        return user
    user = await User.get(id=user_id)

    if not user or user.id != session['user_id']:
        return "Доступ запрещен", 403
    
    lesson_topic = user.course_info[course_idx]["course_settings"].get("lesson")
    if not lesson_topic:
        
        lesson_topic = user.course_info[course_idx]["course"]["4_structure"][0]["3_lessons"][0]["name"]
        user.course_info[course_idx]["course_settings"]["lesson"] = lesson_topic
        await User.filter(id=user.id).update(course_info=user.course_info)

    paid_status = False
    for topic in user.course_info[course_idx]["course"]["4_structure"]:
        for lesson in topic["3_lessons"]:
            if lesson["name"] == lesson_topic:
                paid_status = lesson.get("paid", False)
                break
        if paid_status:
            break

    if not paid_status:
        
        return redirect(url_for('course.course_select', user_id=user_id, course_idx=course_idx))

    conversation_chat = session.get('conversation_chat', [])
    conversation_call = session.get('conversation_call', [])
    conversation = session.get('conversation', [])
    
    with open("conversation_chat.json", "r", encoding="utf-8") as f:
        conversation_chat = json.load(f)
    with open("conversation_call.json", "r", encoding="utf-8") as f:
        conversation_call = json.load(f)
    with open("conversation.json", "r", encoding="utf-8") as f:
        conversation = json.load(f)
    
    lesson_plan = session.get('lesson_plan', "")
    lesson_blocks = session.get('lesson_plan', "").split("<BLOCKS>")[-1].split("</BLOCKS>")[0].split("</block>")
    presentation_history = session.get('presentation_history', "")
    progress = session.get('progress', 0)

    if request.method == 'POST':

        form = await request.form
        files = await request.files
        
        print("[DEBUG] Full POST form:")
        for key, value in form.items():
            print(f"    {key} = {value}")

        print("[DEBUG] POST files:")
        for key, file in files.items():
            print(f"    {key} = {file.filename}, content_type: {file.content_type}, size: {len(file.read())} bytes")
            file.seek(0)  

        print("[DEBUG] Field 'conversation':", form.get("conversation"))
        print("[DEBUG] Field 'response_mode':", form.get("response_mode"))

        form = await request.form
        response_mode = form.get("response_mode", "audio")
        
        conversation_text = form.get('conversation', '').strip()
        if conversation_text:
            
            conversation_chat.append({"role": "user", "content": conversation_text})
            conversation.append({"type": "CHAT", "role": "user", "content": conversation_text})
        import io
        from pydub import AudioSegment
        import os

        files = await request.files
        audio_file = files.get("audio")  
        transcript_result = None

        if audio_file:
            print("[LESSON_CALL] Received audio file:", audio_file.filename)

            audio_bytes = io.BytesIO(audio_file.read())  
            audio_bytes.seek(0)  

            temp_audio_path = "temp_audio.webm"
            with open(temp_audio_path, "wb") as file:
                file.write(audio_bytes.getvalue())
            audio = AudioSegment.from_file(temp_audio_path, format="webm")
            
            try:
                transcript_result = transcribe_audio_with_prepare_data(audio) 
                os.remove(temp_audio_path)
                print("[LESSON_CALL] Transcription:", transcript_result)
                conversation_call.append({"role": "user VOICE", "content": transcript_result})
                conversation.append({"type": "AUDIO TRANSCRIPTION", "role": "user", "content": transcript_result})
            except Exception as e:
                print("[LESSON_CALL] Error transcribing audio:", e)

        if len(user.course_info) <= course_idx:
            return "Course not found", 404

        if not user.course_info[course_idx]["course_settings"].get("lesson"):
            user.course_info[course_idx]["course_settings"]["lesson"] = (
                user.course_info[course_idx]["course"]["4_structure"][0]["3_lessons"][0]["name"]
            )
            await User.filter(id=user.id).update(course_info=user.course_info)

        lesson_topic = user.course_info[course_idx]["course_settings"].get("lesson")

        if lesson_plan == "":
            print("оаоаоаоа")
            payload = {
                "0_content": {
                    "1_user_info": user.user_info,
                    "2_course_info": user.course_info[course_idx]["course"],
                    "3_lesson_topic": lesson_topic,
                },
                "1_type": "lesson_plan"
            }

            response_api = await send_request_to_api(payload)
            lesson_plan = response_api.get("lesson_plan", "")
            lesson_blocks = response_api.get("lesson_plan", "").split("<BLOCKS>")[-1].split("</BLOCKS>")[0].split("</block>")
            print("[LESSON_CALL] API lesson_plan response:", response_api)

        payload = {
            "0_content": {
                "0_conversation_chat": conversation_chat,   
                "0_conversation_call": conversation_call,   
                "0_conversation": conversation,   
                "1_user_info": user.user_info,
                "2_course_info": user.course_info[course_idx]["course"],
                "3_lesson_topic": lesson_topic,
                "4_progress": progress,
                "5_presentation_history": presentation_history,
                "6_lesson_plan": lesson_plan,
                "6_lesson_blocks": lesson_blocks,
                "7_mode": response_mode,
            },
            "1_type": "lesson_call"
        }

        response_api = await send_request_to_api(payload)
        print("[LESSON_CALL] API response:", response_api)

        response_chat = response_api.get("response_chat", "")
        response_call = response_api.get("response_call", None)
        response_call_transcription = response_api.get("response_call_transcription", "")
        response_type = response_api.get("response_type", "")
        status = response_api.get("status", "<OK>")
        presentation_description = response_api.get("presentation_description", "")
        new_progress = response_api.get("progress")
        presentation_image = response_api.get("presentation_image")
        block_tag = response_api.get("block_tag")

        if response_chat:
            if re.sub(r"[^a-zA-Zа-яА-Я]", "", response_chat).lower() == "none":
                response_chat = None
            conversation_chat.append({"role": f"teacher CHAT {response_type}", "content": response_chat, "block_tag": block_tag})
            conversation.append({"type": f"CHAT {response_type}", "role": "teacher", "content": response_chat, "block_tag": block_tag})

        if response_call_transcription:
            conversation_call.append({"role": f"teacher VOICE {response_type}", "content": response_call_transcription, "block_tag": block_tag})
            conversation.append({"type": f"AUDIO TRANSCRIPTION {response_type}", "role": "teacher", "content": response_call_transcription, "block_tag": block_tag})

        if presentation_description:
            presentation_history += (presentation_description + "\n\n")
        
        if new_progress is not None:
            progress = float(new_progress)

        if status == "<END>":
            print("[LESSON_CALL] Lesson ended according to API response")

        session['conversation_chat'] = conversation_chat
        session['conversation_call'] = conversation_call
        session['conversation'] = conversation
        session['progress'] = progress
        session['lesson_plan'] = lesson_plan
        session['presentation_history'] = presentation_history
    
        with open("conversation_chat.json", "w", encoding="utf-8") as f:
            json.dump(conversation_chat, f, ensure_ascii=False, indent=2)
        with open("conversation_call.json", "w", encoding="utf-8") as f:
            json.dump(conversation_call, f, ensure_ascii=False, indent=2)
        with open("conversation.json", "w", encoding="utf-8") as f:
            json.dump(conversation, f, ensure_ascii=False, indent=2)
    
        response_data = {
            "response_chat": response_chat,               
            "response_call": response_call,        
            "audio_input_transcription": transcript_result,
            "response_call_transcription": response_call_transcription,  
            "response_type": response_type,
            "status": status,
            "progress": progress,
            "presentation_image": presentation_image
        }
        return jsonify(response_data)

    session['conversation_chat'] = []
    session['conversation_call'] = []
    session['conversation'] = []
    
    with open("conversation_chat.json", "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)
    with open("conversation_call.json", "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)
    with open("conversation.json", "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)
    
    session['lesson_plan'] = ""
    session['progress'] = 0
    lesson_title = user.course_info[course_idx]["course_settings"].get("lesson", "")
    print("ПРОИЗОШЕЛ ЖЕСТКИЙ GET СУЧКИ")
    return await render_template(
        'lesson_call.html',
        user=user,
        course_idx=course_idx,
        username=user.username,
        lesson_title=lesson_title,
        transcript_history=conversation_call
    )
