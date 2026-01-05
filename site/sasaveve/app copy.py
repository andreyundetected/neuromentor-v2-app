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
