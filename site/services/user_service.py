from models.user import User
from quart import url_for
from quart import redirect
from quart import session



async def require_login():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    if 'language' not in session:
        session['language'] = 'ru'
    user = await User.get(id=session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))
    return user
