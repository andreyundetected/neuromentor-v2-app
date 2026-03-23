from quart import Blueprint, render_template, request, redirect, url_for, session, Response, jsonify
from services.require_login import require_login
from models.user import User
from services.api_service import send_request_to_api

interview_bp = Blueprint('interview', __name__)

@interview_bp.route('/api/check_interview_status')
async def check_interview_status():
    user = await require_login()
    if isinstance(user, Response):
        return jsonify({"has_completed_interview": False})
    
    return jsonify({"has_completed_interview": user.has_completed_interview})

@interview_bp.route('/interview', methods=['GET', 'POST'])
async def interview():
    if 'user_id' not in session:
        return redirect(url_for("auth.login"))

    user = await User.get(id=session['user_id'])

    if request.method == 'POST':
        form = await request.form
        conversation_text = form['conversation']
        conversation = session.get('conversation', [])
        conversation.append({"role": "user", "content": conversation_text})

        payload = {
            "0_content": {
                "0_conversation": conversation,
                "1_user_info": user.user_info
            },
            "1_type": "interview"
        }
        response = await send_request_to_api(payload)

        if response.get("response"):
            conversation.append({"role": "manager", "content": response["response"]})

        session['conversation'] = conversation

        if response.get("user_info"):
            print("Обновление user_info в базе данных")
            user.user_info = response["user_info"]
            if "<END>" in response.get("status"):
                user.has_completed_interview = True
            await user.save()

        return jsonify(response)

    session['conversation'] = []                             
    return await render_template('interview.html', username=user.username)