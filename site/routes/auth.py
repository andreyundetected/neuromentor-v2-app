from models import init_db
from models.user import User
from tortoise import connections
from quart import render_template
from quart import url_for
from quart import redirect
from quart import session
from quart import request
from quart import Blueprint



auth_bp = Blueprint('auth', __name__)


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


async def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))
