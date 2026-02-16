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





async def send_request_to_realtime_api(payload):
    async with aiohttp.ClientSession() as session:
        async with session.post(NEURO_REALTIME_API_URL, json=payload) as response:
            
            async for line in response.content:
                try:
                    piece = json.loads(line.decode('utf-8').strip())
                    yield piece
                except Exception as e:
                    print("Error decoding piece:", e)





@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return redirect(url_for('library'))  
    return redirect(url_for('login'))  

@app.route('/login', methods=['GET', 'POST'])


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


@app.route('/delete_course/<int:course_idx>', methods=['POST'])


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


@app.route('/public_course/<int:course_id>', methods=['GET', 'POST'])


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






@app.route('/stream_audio/<int:user_id>/<int:course_idx>')


@app.route('/course_select/<int:user_id>/<int:course_idx>/lesson_call', methods=['GET', 'POST'])


@app.route('/transcribe', methods=['POST'])


@app.route('/update_course_info/<int:user_id>/<int:course_idx>', methods=['POST'])


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


