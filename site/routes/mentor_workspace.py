from models import User
from models import Mentor
from quart import url_for
from quart import redirect
from quart import render_template
from quart import session
from quart import Blueprint



mentor_workspace = Blueprint("mentor_workspace", __name__)


async def workspace(user_id, mentor_id=None):
    user = await User.get(id=session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))

    if mentor_id is None:
        return await render_template(
            'mentor_workspace.html',
            user=user,
            mentor_id=None,
            mentor_data=None,
            is_new=True
        )

    mentor = await Mentor.filter(id=mentor_id, user_id=user_id).prefetch_related('lessons').first()
    if not mentor:
        return redirect(url_for('mentor_workspace.workspace', user_id=user_id))

    return await render_template(
        'mentor_workspace.html',
        user=user,
        mentor_id=mentor.id,
        mentor_data=mentor,
        lessons=mentor.lessons,
        is_new=False
    )
