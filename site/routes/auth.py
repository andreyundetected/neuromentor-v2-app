from quart import Blueprint, request, session, redirect, url_for, render_template, jsonify, Response
from tortoise import connections
from models.user import User
from models import init_db
from services.user_service import require_login

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
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

@auth_bp.route('/register', methods=['GET', 'POST'])
async def register():
    if not connections._get_storage():
        await init_db()
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

@auth_bp.route('/logout')
async def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

