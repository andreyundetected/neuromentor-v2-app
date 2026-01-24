from tortoise import connections
from transcription import transcribe_audio_with_prepare_data
import re
from collections import Counter
from tortoise import Tortoise
from quart import Response
from quart import jsonify
from quart import request
from quart import render_template
import aiohttp
import os
from quart import url_for
from quart import redirect
from quart import session
from quart import Quart, render_template, request, jsonify, session, Response, redirect, url_for
from tortoise import Tortoise, fields
from tortoise.models import Model
import re
from transcription import transcribe_audio_with_prepare_data
import aiohttp
import json
import os

app = Quart(__name__)
app.secret_key = 'supersecretkey'

DATABASE_URL = os.getenv("DATABASE_URL")

NEURO_API_URL = "http://127.0.0.1:5000/neuro_api"
NEURO_REALTIME_API_URL = "http://127.0.0.1:5000/neuro_realtime_api"

class User(Model):
    id = fields.BigIntField(pk=True)
    username = fields.CharField(max_length=80, unique=True)
    password = fields.CharField(max_length=120)
    user_info = fields.JSONField(default={})
    course_info = fields.JSONField(default=[])
    has_completed_interview = fields.BooleanField(default=False)
    recommendations = fields.JSONField(default=[])
    credits = fields.IntField(default=0)

class PublicCourse(Model):
    id = fields.BigIntField(pk=True)
    name = fields.CharField(max_length=100)
    topic = fields.CharField(max_length=100)
    creator = fields.CharField(max_length=80)
    course_info = fields.JSONField()
    rating = fields.FloatField(default=10.0)

async def init_db():
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={"models": ["app"]}  
    )
    await Tortoise.generate_schemas(safe=True)  

@app.before_serving
async def startup():
    await init_db()

@app.after_serving
async def shutdown():
    await Tortoise.close_connections()

async def send_request_to_api(payload):
    print("Отправка запроса к API с payload:", payload)
    async with aiohttp.ClientSession() as session:
    async with session.post(NEURO_API_URL, json=payload) as response:
        return await response.json()

async def send_request_to_realtime_api(payload):
    async with aiohttp.ClientSession() as session:
        async with session.post(NEURO_REALTIME_API_URL, json=payload) as response:
            
            async for line in response.content:
                try:
                    piece = json.loads(line.decode('utf-8').strip())
                    yield piece
                except Exception as e:
                    print("Error decoding piece:", e)

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
        "5_categories": [],
        "6_teaching_style": "",
        "7_lecture_type": ""
    }

async def require_login():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if 'language' not in session:
        session['language'] = 'ru'

    user = await User.get(id=session['user_id'])

    if not user:
        return redirect(url_for('login'))

    return user  

@app.route('/')
async def index():
    if "user_id" in session:
        user = await User.get(id=session["user_id"])
        if user:
            session["language"] = user.user_info.get("language", "ru")
            return redirect(url_for("library"))
    return redirect(url_for("login"))

@app.route('/login', methods=['GET', 'POST'])
async def login():
    if request.method == 'POST':
        form = await request.form
        username = form['username']
        password = form['password']
        user = await User.filter(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            return "Неверное имя пользователя или пароль"

    return await render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
async def register():
    if request.method == 'POST':
        form = await request.form
        username = form['username']
        password = form['password']

        if await User.filter(username=username).first():
            return "Пользователь уже существует"

        await User.create(username=username, password=password)

        return redirect(url_for('login'))

    return await render_template('register.html')

@app.route('/logout')
async def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/api/check_interview_status')
async def check_interview_status():
    user = await require_login()
    if isinstance(user, Response):
        return jsonify({"has_completed_interview": False})
    
    return jsonify({"has_completed_interview": user.has_completed_interview})

@app.route('/interview', methods=['GET', 'POST'])
async def interview():
    if 'user_id' not in session:
        return redirect(url_for('login'))

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

@app.route('/add_to_library/<int:course_id>', methods=['POST'])
async def add_to_library(course_id):
    user = await require_login()
    if isinstance(user, Response):
        return user

    public_course = await PublicCourse.get(id=course_id)

    if not public_course:
        return "Курс не найден.", 404

    if any(c.get('id') == course_id for c in user.course_info):
        return redirect(url_for('library'))  

    updated_course_info = user.course_info + [{
        **public_course.course_info,
        "id": course_id  
    }]
    
    await User.filter(id=user.id).update(course_info=updated_course_info)

    return redirect(url_for('library'))

@app.route('/delete_course/<int:course_idx>', methods=['POST'])
async def delete_course(course_idx):
    user = await require_login()
    if isinstance(user, Response):
        return user
    user = await User.get(id=session['user_id'])

    if course_idx < 0 or course_idx >= len(user.course_info):
        return "Course not found", 404
    user.course_info.pop(course_idx)
    
    return redirect(url_for('library'))

@app.route('/update_course/<int:course_id>', methods=['POST'])
async def update_course(course_id):
    user = await require_login()
    form = await request.form
    if isinstance(user, Response):
        return user

    course_to_update = await PublicCourse.filter(id=course_id, creator=user.username).first()

    if not course_to_update:
        return "Курс не найден или вы не являетесь его владельцем.", 403

    new_name = form.get('course_name')
    new_topic = form.get('course_topic')

    if new_name:
        course_to_update.name = new_name
    if new_topic:
        course_to_update.topic = new_topic

    return redirect(url_for('index'))

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

    return redirect(url_for('course_creation', user_id=user.id, course_idx=course_idx, start_message=start_message))

def generate_default_recommendations():
    base_recommendation = []
    print(session.get("language"))
    if session.get("language") == "ru":
        base_recommendation = [
            {
                "recommendation_name": "Алгебра для 7 класса",
                "base_json": {
                    "0_topic": "Алгебра",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Курс по Алгебре",
                    "4_structure": [],
                    "5_categories": ["Математика", "Алгебра", "Школа"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Привет! Давай начнем создавать курс по алгебре. Что последнее ты прошел в этой теме?"
            },
            {
                "recommendation_name": "Физика уровня средней школы",
                "base_json": {
                    "0_topic": "Физика",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Курс по физике",
                    "4_structure": [],
                    "5_categories": ["Физика", "Школа"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Привет! Давай начнем создавать курс по физике. Что последнее ты прошел в этой теме?"
            },
            {
                "recommendation_name": "Химия для начинающих",
                "base_json": {
                    "0_topic": "Химия",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Курс по химии",
                    "4_structure": [],
                    "5_categories": ["Химия", "Школа"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Привет! Давай начнем создавать курс по химии. Что последнее ты прошел в этой теме?"
            },
            {
                "recommendation_name": "Биология средних классов",
                "base_json": {
                    "0_topic": "Биология",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Курс по биологии",
                    "4_structure": [],
                    "5_categories": ["Биология", "Школа"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Привет! Давай начнем создавать курс по биологии. Что последнее ты прошел в этой теме?"
            },
            {
                "recommendation_name": "Геометрия. Средняя школа",
                "base_json": {
                    "0_topic": "Геометрия",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Курс по геометрии",
                    "4_structure": [],
                    "5_categories": ["Математика", "Геометрия", "Школа"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Привет! Давай начнем создавать курс по геометрии. Что последнее ты прошел в этой теме?"
            },
            {
                "recommendation_name": "Школьное обществознание",
                "base_json": {
                    "0_topic": "Обществознание",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Курс по обществознанию",
                    "4_structure": [],
                    "5_categories": ["Обществознание", "Школа"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Привет! Давай начнем создавать курс по обществознанию. Что последнее ты прошел в этой теме?"
            }
        ]
    elif session.get("language") == "en":
        base_recommendation = [
            {
                "recommendation_name": "Algebra for 7th Grade",
                "base_json": {
                    "0_topic": "Algebra",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Algebra Course",
                    "4_structure": [],
                    "5_categories": ["Mathematics", "Algebra", "School"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Hello! Let's start creating an algebra course. What is the last topic you studied in this subject?"
            },
            {
                "recommendation_name": "High School Physics",
                "base_json": {
                    "0_topic": "Physics",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Physics Course",
                    "4_structure": [],
                    "5_categories": ["Physics", "School"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Hello! Let's start creating a physics course. What is the last topic you studied in this subject?"
            },
            {
                "recommendation_name": "Beginner Chemistry",
                "base_json": {
                    "0_topic": "Chemistry",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Chemistry Course",
                    "4_structure": [],
                    "5_categories": ["Chemistry", "School"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Hello! Let's start creating a chemistry course. What is the last topic you studied in this subject?"
            },
            {
                "recommendation_name": "Middle School Biology",
                "base_json": {
                    "0_topic": "Biology",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Biology Course",
                    "4_structure": [],
                    "5_categories": ["Biology", "School"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Hello! Let's start creating a biology course. What is the last topic you studied in this subject?"
            },
            {
                "recommendation_name": "Geometry. High School",
                "base_json": {
                    "0_topic": "Geometry",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Geometry Course",
                    "4_structure": [],
                    "5_categories": ["Mathematics", "Geometry", "School"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Hello! Let's start creating a geometry course. What is the last topic you studied in this subject?"
            },
            {
                "recommendation_name": "School Social Studies",
                "base_json": {
                    "0_topic": "Social Studies",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Social Studies Course",
                    "4_structure": [],
                    "5_categories": ["Social Studies", "School"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Hello! Let's start creating a social studies course. What is the last topic you studied in this subject?"
            }
        ]

    return base_recommendation 

from collections import Counter

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

@app.route('/course_creation/<int:user_id>/<int:course_idx>', methods=['GET', 'POST'])
async def course_creation(user_id, course_idx):
    user = await require_login()
    if isinstance(user, Response):
        return user
    if not user.has_completed_interview:
        return await render_template('interview_modal.html')
    user = await User.get(id=user_id)
    if not user or user.id != session['user_id']:
        return "Доступ запрещен", 403

    if session.get("language") == "ru":
        start_message = request.args.get("start_message", "Привет! Это снова я, менеджер. Курс по какой теме тебя интересует?")
    elif session.get("language") == "en":
        start_message = request.args.get("start_message", "Hello! It's me again, the manager. What course topic are you interested in?")

    if start_message and not session.get('conversation'):
        session['conversation'] = [{"role": "manager", "content": start_message}]

    if request.method == 'POST':
        form = await request.form
        print(f"Начинаем обработку генерации курса для user_id={user_id}, course_idx={course_idx}")
        conversation_text = form['conversation']
        conversation = session.get('conversation', [])
        conversation.append({"role": "user", "content": conversation_text})

        if not user.course_info:
            user.course_info = []

        while len(user.course_info) <= course_idx:
            user.course_info.append({
                "course": await get_empty_course_info(),
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
        response = await send_request_to_api(payload)

        if "<END>" in response.get("status"):
            first_lesson = user.course_info[course_idx]["course"]["4_structure"][0]["3_lessons"][0]["name"]
            user.course_info[course_idx]["course_settings"] = {"lesson": first_lesson}
            await User.filter(id=user.id).update(course_info=user.course_info)

        if response.get("response"):
            conversation.append({"role": "manager", "content": response["response"]})

        session['conversation'] = conversation

        if "course_info" in response:
            print(f"Обновление course_info для индекса {course_idx}")
            user.course_info[course_idx]["course"] = response["course_info"]
            print(f"Новое course_info: {user.course_info[course_idx]['course']}")

        try:
            
            await User.filter(id=user.id).update(course_info=user.course_info)
            print("Изменения успешно сохранены в базе данных.")
        except Exception as e:
            print("Ошибка при сохранении в базе данных:", e)

        return jsonify(response)

    session['conversation'] = []  
    
    try:
        course_name = user.course_info[course_idx]["course"]["3_name"]
    except:
        course_name = ""
    return await render_template(
        'course_creation.html',
        user=user,
        course_idx=course_idx,
        username=user.username,
        course_name=course_name,
        start_message=start_message
    )

@app.route('/public_course/<int:course_id>', methods=['GET', 'POST'])
async def public_course_view(course_id):
    user = None
    if 'user_id' in session:
        user = await User.get(id=session['user_id'])

    public_course = await PublicCourse.get(id=course_id)

    if not public_course:
        return "Курс не найден", 404

    if request.method == 'POST':
        form = await request.form
        action = form.get('action')
        if action == 'add_to_library':
            return redirect(url_for('add_to_library', course_id=course_id))
        elif action == 'trial_lesson':
            
            return redirect(url_for('lesson', user_id=user.id, course_idx=0))
    return await render_template(
        'public_course.html',
        user=user,
        course=public_course,
    )

@app.route('/course_edit/<int:user_id>/<int:course_idx>', methods=['GET', 'POST'])
async def course_edit(user_id, course_idx):
    user = await require_login()
    if isinstance(user, Response):
        return user
    user = await User.get(id=user_id)

    if not user or user.id != session['user_id']:
        return "Доступ запрещен", 403

    if request.method == 'POST':
        form = await request.form
        print(f"Начинаем редактирование курса для user_id={user_id}, course_idx={course_idx}")
        conversation_text = form['conversation']
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
        response = await send_request_to_api(payload)

        if response.get("response"):
            conversation.append({"role": "manager", "content": response["response"]})

        session['conversation'] = conversation

        if "course_info" in response:
            print(f"Обновление course_info для индекса {course_idx}")
            user.course_info[course_idx]["course"] = response["course_info"]
            print(f"Новое course_info: {user.course_info[course_idx]['course']}")

        try:
            await User.filter(id=user.id).update(course_info=user.course_info)
            print("Изменения успешно сохранены в базе данных.")
        except Exception as e:
            print("Ошибка при сохранении в базе данных:", e)

        return jsonify(response)

    session['conversation'] = []  
    return await render_template('course_edit.html', user=user, course_idx=course_idx, username=user.username, course_name = user.course_info[course_idx]["course"]["3_name"])

@app.route("/set_language/<lang>", methods=["POST"])
async def set_language(lang):
    """
    Меняет язык пользователя и сохраняет в user_info в базе.
    """

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

@app.route('/course_select/<int:user_id>/<int:course_idx>', methods=['GET', 'POST'])
async def course_select(user_id, course_idx):
    user = await require_login()
    if isinstance(user, Response):
        return user
    user = await User.get(id=user_id)
    if not user or user.id != session['user_id']:
        return "Доступ запрещен", 403

    if not user or course_idx >= len(user.course_info):
        return "Курс не найден", 404

    course = user.course_info[course_idx]["course"]  

    if "4_structure" not in course or not course["4_structure"]:
        print(f"Курс {course_idx} не завершен. Перенаправляем на создание.")
        return redirect(url_for('course_creation', user_id=user_id, course_idx=course_idx))
    
    if "lesson" not in user.course_info[course_idx]["course_settings"]:
        try:
            first_lesson = course["4_structure"][0]["3_lessons"][0]["name"]
            user.course_info[course_idx]["course_settings"]["lesson"] = first_lesson
            await User.filter(id=user.id).update(course_info=user.course_info)
            print(f"Задан первый урок для курса {course_idx}: {first_lesson}")
        except (IndexError, KeyError):
            print(f"Ошибка: невозможно задать первый урок для курса {course_idx}, 4_structure пуст или некорректен")

    for topic in course["4_structure"]:
        for i, lesson in enumerate(topic["3_lessons"]):
            if "paid" not in lesson:
                
                lesson["paid"] = (topic == course["4_structure"][0] and i == 0)
    
    await User.filter(id=user.id).update(course_info=user.course_info)

    next_lesson = user.course_info[course_idx]["course_settings"].get("lesson", None)
    next_lesson_paid = False
    if next_lesson:
        for topic in course["4_structure"]:
            for lesson in topic["3_lessons"]:
                if lesson["name"] == next_lesson:
                    next_lesson_paid = lesson.get("paid", False)
                    break
            if next_lesson_paid:
                break

    if request.method == 'POST':
        form = await request.form
        action = form.get('action')
        print("0000000000", action)
        if action == 'lesson':
        
            if next_lesson_paid:
                print("oplac")
                return redirect(url_for('lesson_call', user_id=user_id, course_idx=course_idx))
            else:
                
                print("ne oplac")
                if user.credits > 0:
                    print(">0")
                    
                    user.credits -= 1
                    await User.filter(id=user.id).update(credits=user.credits)
                    
                    for topic in course["4_structure"]:
                        for lesson in topic["3_lessons"]:
                            if lesson["name"] == next_lesson:
                                lesson["paid"] = True
                                break
                    await User.filter(id=user.id).update(course_info=user.course_info)
                    
                    return redirect(url_for('lesson_call', user_id=user_id, course_idx=course_idx))
                else:
                    print("<=0")
                    
                    total_lessons = 0
                    completed_lessons = 0
                    found = False
                    for topic in course["4_structure"]:
                        total_lessons += len(topic["3_lessons"])
                        for lesson in topic["3_lessons"]:
                            
                            if lesson["name"] == user.course_info[course_idx]["course_settings"].get("lesson"):
                                found = True
                            if not found:
                                completed_lessons += 1

                    progress = (completed_lessons / total_lessons) * 100
                    return await render_template(
                        'course_select.html',
                        user=user,
                        course=course,
                        course_idx=course_idx,
                        username=user.username,
                        progress=progress,
                        course_id=course_idx,
                        next_lesson=next_lesson,
                        next_lesson_paid=next_lesson_paid,
                        insufficient_credits=True
                    )
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
    await User.filter(id=user.id).update(course_info=user.course_info)

    next_lesson = user.course_info[course_idx]["course_settings"].get("lesson", None)
    
    return await render_template('course_select.html', user=user, course=course, course_idx=course_idx, username=user.username, progress = progress, course_id = course_idx, next_lesson=next_lesson, next_lesson_paid=next_lesson_paid)

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
    """
    Логика:
      - conversation_chat -> содержит текстовые сообщения
      - conversation_call -> содержит транскрипции аудио
      - POST:
         1) Принимаем текст и/или аудио
         2) Транскрибируем аудио -> добавляем в conversation_call
         3) Собираем payload -> отправляем в API
         4) Из ответа:
            - response -> добавляем в conversation_chat
            - response_call -> отдаем клиенту (Base64 MP3)
            - response_call_transcription -> добавляем в conversation_call
            - progress -> обновляем
            - status == <END> -> завершаем урок
         5) Возвращаем JSON клиенту

      - GET:
         Очищаем conversation_chat, conversation_call, progress
         Рендерим lesson_call.html
    """

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
        
        return redirect(url_for('course_select', user_id=user_id, course_idx=course_idx))

    conversation_chat = session.get('conversation_chat', [])
    conversation_call = session.get('conversation_call', [])
    lesson_plan = session.get('lesson_plan', "")
    presentation_history = session.get('presentation_history', "")
    progress = session.get('progress', 0)

    if request.method == 'POST':
        form = await request.form
        response_mode = form.get("response_mode", "audio")
        
        conversation_text = form.get('conversation', '').strip()
        if conversation_text:
            
            conversation_chat.append({"role": "user", "content": conversation_text})
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
            print("[LESSON_CALL] API lesson_plan response:", response_api)

        payload = {
            "0_content": {
                "0_conversation_chat": conversation_chat,   
                "0_conversation_call": conversation_call,   
                "1_user_info": user.user_info,
                "2_course_info": user.course_info[course_idx]["course"],
                "3_lesson_topic": lesson_topic,
                "4_progress": progress,
                "5_presentation_history": presentation_history,
                "6_lesson_plan": lesson_plan,
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
        presentation_code = response_api.get("presentation_code", "")
        new_progress = response_api.get("progress")
        presentation_image = response_api.get("presentation_image")

        if response_chat:
            if re.sub(r"[^a-zA-Zа-яА-Я]", "", response_chat).lower() == "none":
                response_chat = None
            conversation_chat.append({"role": f"teacher CHAT {response_type}", "content": response_chat})

        if response_call_transcription:
            conversation_call.append({"role": f"teacher VOICE {response_type}", "content": response_call_transcription})

        if presentation_code:
            presentation_history += (presentation_code + "\n\n")

        if new_progress is not None:
            progress = float(new_progress)

        if status == "<END>":
            print("[LESSON_CALL] Lesson ended according to API response")

        session['conversation_chat'] = conversation_chat
        session['conversation_call'] = conversation_call
        session['progress'] = progress
        session['lesson_plan'] = lesson_plan

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
        print("==========")
        print(conversation_call)
        print(conversation_chat)
        return jsonify(response_data)

    session['conversation_chat'] = []
    session['conversation_call'] = []
    session['progress'] = 0
    lesson_title = user.course_info[course_idx]["course_settings"].get("lesson", "")
    return await render_template(
        'lesson_call.html',
        user=user,
        course_idx=course_idx,
        username=user.username,
        lesson_title=lesson_title,
        transcript_history=conversation_call
    )

@app.route('/update_course_info/<int:user_id>/<int:course_idx>', methods=['POST'])
async def update_course_info(user_id, course_idx):
    user = await User.get(id=user_id)
    form = await request.form

    if not user:
        return redirect(url_for('login'))
    
    course_name = form.get('course_name')
    learning_format = form.get('learning_format')
    lecture_type = form.get('lecture_type')
    
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
    
    session.modified = True
    
    return redirect(url_for('course_settings', user_id=user.id, course_idx=course_idx))

@app.route('/course_settings/<int:user_id>/<int:course_idx>')
async def course_settings(user_id, course_idx):
    user = await User.get(id=user_id)

    if not user:
        return redirect(url_for('login'))
    
    course_info = user.course_info[course_idx]["course"]
    course_settings = session.get('course_settings', {}).get(course_idx, [])
    
    nearest_lesson = None
    for setting in course_settings:
        if not setting['completed']:
            nearest_lesson = setting['name']
            break
    
    return await render_template(
        'course_settings.html',
        user=user,
        course_idx=course_idx,
        course_info=course_info,
        course_settings=course_settings,
        nearest_lesson=nearest_lesson
    )

if __name__ == '__main__':
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)


class User(Model):
    id = fields.BigIntField(pk=True)
    username = fields.CharField(max_length=80, unique=True)
    password = fields.CharField(max_length=120)
    user_info = fields.JSONField(default={})
    course_info = fields.JSONField(default=[])
    has_completed_interview = fields.BooleanField(default=False)
    recommendations = fields.JSONField(default=[])
    credits = fields.IntField(default=0)


async def require_login():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if 'language' not in session:
        session['language'] = 'ru'

    user = await User.get(id=session['user_id'])

    if not user:
        return redirect(url_for('login'))

    return user


NEURO_API_URL = "https://" + os.getenv("NEURO_API-DOMAIN", "") + "/neuro_api"


async def send_request_to_api(payload):
    print("Отправка запроса к API с payload:", payload)
    async with aiohttp.ClientSession() as session:
        async with session.post(NEURO_API_URL, json=payload) as response:
            return await response.json()


async def course_edit(user_id, course_idx):
    user = await require_login()
    if isinstance(user, Response):
        return user
    user = await User.get(id=user_id)

    if not user or user.id != session['user_id']:
        return "Доступ запрещен", 403

    if request.method == 'POST':
        form = await request.form
        print(f"Начинаем редактирование курса для user_id={user_id}, course_idx={course_idx}")
        conversation_text = form['conversation']
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
        response = await send_request_to_api(payload)

        if response.get("response"):
            conversation.append({"role": "manager", "content": response["response"]})

        session['conversation'] = conversation

        if "course_info" in response:
            print(f"Обновление course_info для индекса {course_idx}")
            user.course_info[course_idx]["course"] = response["course_info"]
            print(f"Новое course_info: {user.course_info[course_idx]['course']}")

        try:
            await User.filter(id=user.id).update(course_info=user.course_info)
            print("Изменения успешно сохранены в базе данных.")
        except Exception as e:
            print("Ошибка при сохранении в базе данных:", e)

        return jsonify(response)

    session['conversation'] = []  
    return await render_template('course_edit.html', user=user, course_idx=course_idx, username=user.username, course_name = user.course_info[course_idx]["course"]["3_name"])


async def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))


class PublicCourse(Model):
    id = fields.BigIntField(pk=True)
    name = fields.CharField(max_length=100)
    topic = fields.CharField(max_length=100)
    creator = fields.CharField(max_length=80)
    course_info = fields.JSONField()
    rating = fields.FloatField(default=10.0)


async def public_course_view(course_id):
    user = None
    if 'user_id' in session:
        user = await User.get(id=session['user_id'])

    public_course = await PublicCourse.get(id=course_id)

    if not public_course:
        return "Курс не найден", 404

    if request.method == 'POST':
        form = await request.form
        action = form.get('action')
        if action == 'add_to_library':
            return redirect(url_for('add_to_library', course_id=course_id))
        elif action == 'trial_lesson':
            
            return redirect(url_for('lesson', user_id=user.id, course_idx=0))
    return await render_template(
        'public_course.html',
        user=user,
        course=public_course,
    )


async def index():
    if "user_id" in session:
        user = await User.get(id=session["user_id"])
        if user:
            session["language"] = user.user_info.get("language", "ru")
            return redirect(url_for("library"))
    return redirect(url_for("login"))


async def shutdown():
    await Tortoise.close_connections()


async def update_course(course_id):
    user = await require_login()
    form = await request.form
    if isinstance(user, Response):
        return user

    course_to_update = await PublicCourse.filter(id=course_id, creator=user.username).first()

    if not course_to_update:
        return "Курс не найден или вы не являетесь его владельцем.", 403

    new_name = form.get('course_name')
    new_topic = form.get('course_topic')

    if new_name:
        course_to_update.name = new_name
    if new_topic:
        course_to_update.topic = new_topic

    return redirect(url_for('index'))


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


def generate_default_recommendations():
    base_recommendation = []
    print(session.get("language"))
    if session.get("language") == "ru":
        base_recommendation = [
            {
                "recommendation_name": "Алгебра для 7 класса",
                "base_json": {
                    "0_topic": "Алгебра",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Курс по Алгебре",
                    "4_structure": [],
                    "5_categories": ["Математика", "Алгебра", "Школа"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Привет! Давай начнем создавать курс по алгебре. Что последнее ты прошел в этой теме?"
            },
            {
                "recommendation_name": "Физика уровня средней школы",
                "base_json": {
                    "0_topic": "Физика",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Курс по физике",
                    "4_structure": [],
                    "5_categories": ["Физика", "Школа"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Привет! Давай начнем создавать курс по физике. Что последнее ты прошел в этой теме?"
            },
            {
                "recommendation_name": "Химия для начинающих",
                "base_json": {
                    "0_topic": "Химия",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Курс по химии",
                    "4_structure": [],
                    "5_categories": ["Химия", "Школа"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Привет! Давай начнем создавать курс по химии. Что последнее ты прошел в этой теме?"
            },
            {
                "recommendation_name": "Биология средних классов",
                "base_json": {
                    "0_topic": "Биология",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Курс по биологии",
                    "4_structure": [],
                    "5_categories": ["Биология", "Школа"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Привет! Давай начнем создавать курс по биологии. Что последнее ты прошел в этой теме?"
            },
            {
                "recommendation_name": "Геометрия. Средняя школа",
                "base_json": {
                    "0_topic": "Геометрия",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Курс по геометрии",
                    "4_structure": [],
                    "5_categories": ["Математика", "Геометрия", "Школа"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Привет! Давай начнем создавать курс по геометрии. Что последнее ты прошел в этой теме?"
            },
            {
                "recommendation_name": "Школьное обществознание",
                "base_json": {
                    "0_topic": "Обществознание",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Курс по обществознанию",
                    "4_structure": [],
                    "5_categories": ["Обществознание", "Школа"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Привет! Давай начнем создавать курс по обществознанию. Что последнее ты прошел в этой теме?"
            }
        ]
    elif session.get("language") == "en":
        base_recommendation = [
            {
                "recommendation_name": "Algebra for 7th Grade",
                "base_json": {
                    "0_topic": "Algebra",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Algebra Course",
                    "4_structure": [],
                    "5_categories": ["Mathematics", "Algebra", "School"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Hello! Let's start creating an algebra course. What is the last topic you studied in this subject?"
            },
            {
                "recommendation_name": "High School Physics",
                "base_json": {
                    "0_topic": "Physics",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Physics Course",
                    "4_structure": [],
                    "5_categories": ["Physics", "School"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Hello! Let's start creating a physics course. What is the last topic you studied in this subject?"
            },
            {
                "recommendation_name": "Beginner Chemistry",
                "base_json": {
                    "0_topic": "Chemistry",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Chemistry Course",
                    "4_structure": [],
                    "5_categories": ["Chemistry", "School"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Hello! Let's start creating a chemistry course. What is the last topic you studied in this subject?"
            },
            {
                "recommendation_name": "Middle School Biology",
                "base_json": {
                    "0_topic": "Biology",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Biology Course",
                    "4_structure": [],
                    "5_categories": ["Biology", "School"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Hello! Let's start creating a biology course. What is the last topic you studied in this subject?"
            },
            {
                "recommendation_name": "Geometry. High School",
                "base_json": {
                    "0_topic": "Geometry",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Geometry Course",
                    "4_structure": [],
                    "5_categories": ["Mathematics", "Geometry", "School"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Hello! Let's start creating a geometry course. What is the last topic you studied in this subject?"
            },
            {
                "recommendation_name": "School Social Studies",
                "base_json": {
                    "0_topic": "Social Studies",
                    "1_initial_level": "",
                    "2_target_level": "",
                    "3_name": "Social Studies Course",
                    "4_structure": [],
                    "5_categories": ["Social Studies", "School"],
                    "6_teaching_style": "",
                    "7_lecture_type": "podcast"
                },
                "start_message": "Hello! Let's start creating a social studies course. What is the last topic you studied in this subject?"
            }
        ]

    return base_recommendation


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


DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql://", "postgres://")


async def init_db():
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={"models": ["__main__"]}  
    )
    await Tortoise.generate_schemas(safe=True)


async def startup():
    await init_db()


async def login():
    if request.method == 'POST':
        form = await request.form
        username = form['username']
        password = form['password']
        user = await User.filter(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            return "Неверное имя пользователя или пароль"

    return await render_template('login.html')


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
        
        return redirect(url_for('course_select', user_id=user_id, course_idx=course_idx))

    conversation_chat = session.get('conversation_chat', [])
    conversation_call = session.get('conversation_call', [])
    lesson_plan = session.get('lesson_plan', "")
    presentation_history = session.get('presentation_history', "")
    progress = session.get('progress', 0)

    if request.method == 'POST':
        form = await request.form
        response_mode = form.get("response_mode", "audio")
        
        conversation_text = form.get('conversation', '').strip()
        if conversation_text:
            
            conversation_chat.append({"role": "user", "content": conversation_text})
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
            print("[LESSON_CALL] API lesson_plan response:", response_api)

        payload = {
            "0_content": {
                "0_conversation_chat": conversation_chat,   
                "0_conversation_call": conversation_call,   
                "1_user_info": user.user_info,
                "2_course_info": user.course_info[course_idx]["course"],
                "3_lesson_topic": lesson_topic,
                "4_progress": progress,
                "5_presentation_history": presentation_history,
                "6_lesson_plan": lesson_plan,
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
        presentation_code = response_api.get("presentation_code", "")
        new_progress = response_api.get("progress")
        presentation_image = response_api.get("presentation_image")

        if response_chat:
            if re.sub(r"[^a-zA-Zа-яА-Я]", "", response_chat).lower() == "none":
                response_chat = None
            conversation_chat.append({"role": f"teacher CHAT {response_type}", "content": response_chat})

        if response_call_transcription:
            conversation_call.append({"role": f"teacher VOICE {response_type}", "content": response_call_transcription})

        if presentation_code:
            presentation_history += (presentation_code + "\n\n")

        if new_progress is not None:
            progress = float(new_progress)

        if status == "<END>":
            print("[LESSON_CALL] Lesson ended according to API response")

        session['conversation_chat'] = conversation_chat
        session['conversation_call'] = conversation_call
        session['progress'] = progress
        session['lesson_plan'] = lesson_plan

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
        print("==========")
        print(conversation_call)
        print(conversation_chat)
        return jsonify(response_data)

    session['conversation_chat'] = []
    session['conversation_call'] = []
    session['progress'] = 0
    lesson_title = user.course_info[course_idx]["course_settings"].get("lesson", "")
    return await render_template(
        'lesson_call.html',
        user=user,
        course_idx=course_idx,
        username=user.username,
        lesson_title=lesson_title,
        transcript_history=conversation_call
    )


async def delete_course(course_idx):
    user = await require_login()
    if isinstance(user, Response):
        return user
    user = await User.get(id=session['user_id'])

    if course_idx < 0 or course_idx >= len(user.course_info):
        return "Course not found", 404
    user.course_info.pop(course_idx)
    
    return redirect(url_for('library'))


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

    return redirect(url_for('course_creation', user_id=user.id, course_idx=course_idx, start_message=start_message))


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
        "5_categories": [],
        "6_teaching_style": "",
        "7_lecture_type": ""
    }


async def course_creation(user_id, course_idx):
    user = await require_login()
    if isinstance(user, Response):
        return user
    if not user.has_completed_interview:
        return await render_template('interview_modal.html')
    user = await User.get(id=user_id)
    if not user or user.id != session['user_id']:
        return "Доступ запрещен", 403

    if session.get("language") == "ru":
        start_message = request.args.get("start_message", "Привет! Это снова я, менеджер. Курс по какой теме тебя интересует?")
    elif session.get("language") == "en":
        start_message = request.args.get("start_message", "Hello! It's me again, the manager. What course topic are you interested in?")

    if start_message and not session.get('conversation'):
        session['conversation'] = [{"role": "manager", "content": start_message}]

    if request.method == 'POST':
        form = await request.form
        print(f"Начинаем обработку генерации курса для user_id={user_id}, course_idx={course_idx}")
        conversation_text = form['conversation']
        conversation = session.get('conversation', [])
        conversation.append({"role": "user", "content": conversation_text})

        if not user.course_info:
            user.course_info = []

        while len(user.course_info) <= course_idx:
            user.course_info.append({
                "course": await get_empty_course_info(),
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
        response = await send_request_to_api(payload)

        if "<END>" in response.get("status"):
            first_lesson = user.course_info[course_idx]["course"]["4_structure"][0]["3_lessons"][0]["name"]
            user.course_info[course_idx]["course_settings"] = {"lesson": first_lesson}
            await User.filter(id=user.id).update(course_info=user.course_info)

        if response.get("response"):
            conversation.append({"role": "manager", "content": response["response"]})

        session['conversation'] = conversation

        if "course_info" in response:
            print(f"Обновление course_info для индекса {course_idx}")
            user.course_info[course_idx]["course"] = response["course_info"]
            print(f"Новое course_info: {user.course_info[course_idx]['course']}")

        try:
            
            await User.filter(id=user.id).update(course_info=user.course_info)
            print("Изменения успешно сохранены в базе данных.")
        except Exception as e:
            print("Ошибка при сохранении в базе данных:", e)

        return jsonify(response)

    session['conversation'] = []  
    
    try:
        course_name = user.course_info[course_idx]["course"]["3_name"]
    except:
        course_name = ""
    return await render_template(
        'course_creation.html',
        user=user,
        course_idx=course_idx,
        username=user.username,
        course_name=course_name,
        start_message=start_message
    )


async def add_to_library(course_id):
    user = await require_login()
    if isinstance(user, Response):
        return user

    public_course = await PublicCourse.get(id=course_id)

    if not public_course:
        return "Курс не найден.", 404

    if any(c.get('id') == course_id for c in user.course_info):
        return redirect(url_for('library'))  

    updated_course_info = user.course_info + [{
        **public_course.course_info,
        "id": course_id  
    }]
    
    await User.filter(id=user.id).update(course_info=updated_course_info)

    return redirect(url_for('library'))


async def course_settings(user_id, course_idx):
    user = await User.get(id=user_id)

    if not user:
        return redirect(url_for('login'))
    
    course_info = user.course_info[course_idx]["course"]
    course_settings = session.get('course_settings', {}).get(course_idx, [])
    
    nearest_lesson = None
    for setting in course_settings:
        if not setting['completed']:
            nearest_lesson = setting['name']
            break
    
    return await render_template(
        'course_settings.html',
        user=user,
        course_idx=course_idx,
        course_info=course_info,
        course_settings=course_settings,
        nearest_lesson=nearest_lesson
    )


async def update_course_info(user_id, course_idx):
    user = await User.get(id=user_id)
    form = await request.form

    if not user:
        return redirect(url_for('login'))
    
    course_name = form.get('course_name')
    learning_format = form.get('learning_format')
    lecture_type = form.get('lecture_type')
    
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
    
    session.modified = True
    
    return redirect(url_for('course_settings', user_id=user.id, course_idx=course_idx))


async def ensure_db_connection():
    if not connections._get_storage():
        await init_db()


async def register():
    await ensure_db_connection()
    if request.method == 'POST':
        form = await request.form
        username = form['username']
        password = form['password']

        if await User.filter(username=username).first():
            return "Пользователь уже существует"

        user = await User.create(username=username, password=password)
        session['user_id'] = user.id
        return redirect(url_for('library'))

    return await render_template('register.html')


async def check_interview_status():
    user = await require_login()
    if isinstance(user, Response):
        return jsonify({"has_completed_interview": False})
    
    return jsonify({"has_completed_interview": user.has_completed_interview})


async def course_select(user_id, course_idx):
    user = await require_login()
    if isinstance(user, Response):
        return user
    user = await User.get(id=user_id)
    if not user or user.id != session['user_id']:
        return "Доступ запрещен", 403

    if not user or course_idx >= len(user.course_info):
        return "Курс не найден", 404

    course = user.course_info[course_idx]["course"]  

    if "4_structure" not in course or not course["4_structure"]:
        print(f"Курс {course_idx} не завершен. Перенаправляем на создание.")
        return redirect(url_for('course_creation', user_id=user_id, course_idx=course_idx))
    
    if "lesson" not in user.course_info[course_idx]["course_settings"]:
        try:
            first_lesson = course["4_structure"][0]["3_lessons"][0]["name"]
            user.course_info[course_idx]["course_settings"]["lesson"] = first_lesson
            await User.filter(id=user.id).update(course_info=user.course_info)
            print(f"Задан первый урок для курса {course_idx}: {first_lesson}")
        except (IndexError, KeyError):
            print(f"Ошибка: невозможно задать первый урок для курса {course_idx}, 4_structure пуст или некорректен")

    for topic in course["4_structure"]:
        for i, lesson in enumerate(topic["3_lessons"]):
            if "paid" not in lesson:
                
                lesson["paid"] = (topic == course["4_structure"][0] and i == 0)
    
    await User.filter(id=user.id).update(course_info=user.course_info)

    next_lesson = user.course_info[course_idx]["course_settings"].get("lesson", None)
    next_lesson_paid = False
    if next_lesson:
        for topic in course["4_structure"]:
            for lesson in topic["3_lessons"]:
                if lesson["name"] == next_lesson:
                    next_lesson_paid = lesson.get("paid", False)
                    break
            if next_lesson_paid:
                break

    if request.method == 'POST':
        form = await request.form
        action = form.get('action')
        print("0000000000", action)
        if action == 'lesson':
        
            if next_lesson_paid:
                print("oplac")
                return redirect(url_for('lesson_call', user_id=user_id, course_idx=course_idx))
            else:
                
                print("ne oplac")
                if user.credits > 0:
                    print(">0")
                    
                    user.credits -= 1
                    await User.filter(id=user.id).update(credits=user.credits)
                    
                    for topic in course["4_structure"]:
                        for lesson in topic["3_lessons"]:
                            if lesson["name"] == next_lesson:
                                lesson["paid"] = True
                                break
                    await User.filter(id=user.id).update(course_info=user.course_info)
                    
                    return redirect(url_for('lesson_call', user_id=user_id, course_idx=course_idx))
                else:
                    print("<=0")
                    
                    total_lessons = 0
                    completed_lessons = 0
                    found = False
                    for topic in course["4_structure"]:
                        total_lessons += len(topic["3_lessons"])
                        for lesson in topic["3_lessons"]:
                            
                            if lesson["name"] == user.course_info[course_idx]["course_settings"].get("lesson"):
                                found = True
                            if not found:
                                completed_lessons += 1

                    progress = (completed_lessons / total_lessons) * 100
                    return await render_template(
                        'course_select.html',
                        user=user,
                        course=course,
                        course_idx=course_idx,
                        username=user.username,
                        progress=progress,
                        course_id=course_idx,
                        next_lesson=next_lesson,
                        next_lesson_paid=next_lesson_paid,
                        insufficient_credits=True
                    )
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
    await User.filter(id=user.id).update(course_info=user.course_info)

    next_lesson = user.course_info[course_idx]["course_settings"].get("lesson", None)
    
    return await render_template('course_select.html', user=user, course=course, course_idx=course_idx, username=user.username, progress = progress, course_id = course_idx, next_lesson=next_lesson, next_lesson_paid=next_lesson_paid)


app.secret_key = 'supersecretkey'


if __name__ == '__main__':
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)


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
