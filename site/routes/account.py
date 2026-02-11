import re
from models.user import User
from services.require_login import require_login
from quart import Response
from quart import session
from quart import request
from quart import render_template
from quart import Blueprint



account_bp = Blueprint('account', __name__)


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
