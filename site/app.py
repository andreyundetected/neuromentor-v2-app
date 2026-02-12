from quart import Quart, render_template, request, jsonify, session, Response, redirect, url_for
from tortoise import Tortoise, fields
from tortoise.models import Model
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