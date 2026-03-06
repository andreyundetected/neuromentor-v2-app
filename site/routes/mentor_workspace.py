from quart import Blueprint, request, session, render_template, redirect, url_for, jsonify
from models import Mentor, Lesson, User
from uuid import uuid4

mentor_workspace = Blueprint("mentor_workspace", __name__)

@mentor_workspace.route('/mentor_workspace/<int:user_id>/', methods=['GET'])
@mentor_workspace.route('/mentor_workspace/<int:user_id>/<string:mentor_id>', methods=['GET'])
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
