from models.user import User
from quart import session
from quart import Blueprint



utils_bp = Blueprint('utils', __name__)


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
