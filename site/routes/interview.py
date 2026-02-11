from services.require_login import require_login
from quart import jsonify
from quart import Response
from quart import Blueprint



interview_bp = Blueprint('interview', __name__)


async def check_interview_status():
    user = await require_login()
    if isinstance(user, Response):
        return jsonify({"has_completed_interview": False})
    
    return jsonify({"has_completed_interview": user.has_completed_interview})
