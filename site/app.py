from quart import Quart, render_template, request, jsonify, session, Response, redirect, url_for
from tortoise import Tortoise, fields, connections
from tortoise.models import Model
import re
from services.api_service import send_request_to_api
import os
from models import init_db
from routes import blueprints
from models.user import User
from services.require_login import require_login

app = Quart(__name__)
app.secret_key = 'supersecretkey'

for bp in blueprints:
    app.register_blueprint(bp)

DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql://", "postgres://")

NEURO_API_URL = "https://" + os.getenv("NEURO_API-DOMAIN", "") + "/neuro_api"

class PublicCourse(Model):
    id = fields.BigIntField(pk=True)
    name = fields.CharField(max_length=100)
    topic = fields.CharField(max_length=100)
    creator = fields.CharField(max_length=80)
    course_info = fields.JSONField()
    rating = fields.FloatField(default=10.0)

@app.before_serving
async def startup():
    await init_db(DATABASE_URL)

@app.after_serving
async def shutdown():
    await Tortoise.close_connections()





@app.route('/api/check_interview_status')


@app.route('/interview', methods=['GET', 'POST'])
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

@app.route('/start_recommendation/<int:recommendation_idx>', methods=['GET', 'POST'])
async def start_recommendation(recommendation_idx):
    user = await require_login()
    if isinstance(user, Response):
        return user

    if recommendation_idx >= len(user.recommendations):
        return "Recommendation not found", 404

    recommendation = user.recommendations[recommendation_idx]
    base_json = recommendation.get("base_json", {})
    start_message = recommendation.get("start_message", "Welcome to your recommended course!")

    if not user.course_info:
        user.course_info = []
    
    course_idx = len(user.course_info)
    user.course_info.append({"course": base_json, "course_settings": {}})
    await User.filter(id=user.id).update(course_info=user.course_info)

    return redirect(url_for('course.course_creation', user_id=user.id, course_idx=course_idx, start_message=start_message))

@app.route('/account', methods=['GET', 'POST'])
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

@app.route("/set_language/<lang>", methods=["POST"])
async def set_language(lang):

    if lang not in ["ru", "en"]:
        lang = "ru"

    user_id = session.get("user_id")
    if not user_id:
        return "Unauthorized", 401

    user = await User.get(id=user_id)

    if not user:
        return "User not found", 404

    user.user_info["language"] = lang
    await User.filter(id=user.id).update(user_info=user.user_info)

    session["language"] = lang

    return "", 204  

if __name__ == '__main__':
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)