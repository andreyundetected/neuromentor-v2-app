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
