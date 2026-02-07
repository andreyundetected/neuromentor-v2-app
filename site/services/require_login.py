from quart import session, redirect, url_for
from models.user import User

async def require_login():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    if 'language' not in session:
        session['language'] = 'ru'
    user = await User.get(id=session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))
    return user
