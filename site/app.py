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

if __name__ == '__main__':
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)