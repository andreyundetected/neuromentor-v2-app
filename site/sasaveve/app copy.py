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





















@app.route('/')
  

@app.route('/login', methods=['GET', 'POST'])


@app.route('/register', methods=['GET', 'POST'])


@app.route('/logout')


@app.route('/interview', methods=['GET', 'POST'])


@app.route('/add_to_library/<int:course_id>', methods=['POST'])


@app.route('/delete_course/<int:course_idx>', methods=['POST'])


@app.route('/update_course/<int:course_id>', methods=['POST'])


@app.route('/library')


@app.route('/account', methods=['GET', 'POST'])


@app.route('/course_creation/<int:user_id>/<int:course_idx>', methods=['GET', 'POST'])


@app.route('/public_course/<int:course_id>', methods=['GET', 'POST'])


@app.route('/course_edit/<int:user_id>/<int:course_idx>', methods=['GET', 'POST'])


@app.route('/course_select/<int:user_id>/<int:course_idx>', methods=['GET', 'POST'])


@app.route('/course_select/<int:user_id>/<int:course_idx>/lesson_chat', methods=['GET', 'POST'])






@app.route('/stream_audio/<int:user_id>/<int:course_idx>')


@app.route('/course_select/<int:user_id>/<int:course_idx>/lesson_call', methods=['GET', 'POST'])


@app.route('/transcribe', methods=['POST'])


@app.route('/update_course_info/<int:user_id>/<int:course_idx>', methods=['POST'])


@app.route('/course_settings/<int:user_id>/<int:course_idx>')



