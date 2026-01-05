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
