from models.user import User
from quart import Blueprint, request, session, render_template, redirect, url_for, jsonify
from models import Mentor, Lesson, User
from uuid import uuid4

mentor_workspace = Blueprint("mentor_workspace", __name__)

@mentor_workspace.route('/mentor_workspace/<int:user_id>/', methods=['GET'])
@mentor_workspace.route('/mentor_workspace/<int:user_id>/<string:mentor_id>', methods=['GET'])
async def workspace(user_id: int):
    session_user_id = session.get("user_id")
    if not session_user_id:
        return redirect(url_for("auth.login"))

    if session_user_id != user_id:
        return redirect(url_for("mentor_workspace.workspace", user_id=session_user_id))

    user = await User.get_or_none(id=session_user_id)
    if not user:
        return redirect(url_for("auth.login"))

    return await render_template(
        "mentor_workspace.html",
        user=user,
        mentor_id=None,
        mentor_data=None,
        lessons=[],     
        is_new=True,
        avatar_options=AVATAR_OPTIONS,
    )


AVATAR_OPTIONS = [
    {"id": "bot_blue", "url": "https://img.icons8.com/color/96/bot.png", "label": "Bot Blue"},
    {"id": "mentor_male", "url": "https://img.icons8.com/color/96/teacher.png", "label": "Mentor Male"},
    {"id": "mentor_female", "url": "https://img.icons8.com/color/96/training.png", "label": "Mentor Female"},
    {"id": "owl", "url": "https://img.icons8.com/color/96/owl.png", "label": "Owl"},
]


async def mentor_intro(user_id: int):
    session_user_id = session.get("user_id")
    if not session_user_id or session_user_id != user_id:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    payload = await request.get_json(force=True, silent=True) or {}
    name: str = (payload.get("name") or "").strip()
    specs = payload.get("specializations") or []
    language: str = (payload.get("language") or "en").strip().lower()
    style: str = (payload.get("style") or "").strip()
    voice: str = (payload.get("voice") or "").strip().lower()
    avatar_id: str = (payload.get("avatar_id") or "").strip()

    if not name:
        name = "Mentor" if language == "en" else "Ментор"

    avatar_url = None
    for a in AVATAR_OPTIONS:
        if a["id"] == avatar_id:
            avatar_url = a["url"]
            break

    if language == "ru":
        msg = f"Привет! Я {name}. Давай создадим план обучения."
        hint = "Заполни поля слева, а затем напиши, что хочешь изучать."
        send_label = "Отправить"
    else:
        msg = f"Hi! I’m {name}. Let’s create your learning plan."
        hint = "Fill the fields on the left, then tell me what you want to learn."
        send_label = "Send"

    return jsonify({
        "ok": True,
        "unlock_chat": True,
        "mentor_name": name,
        "avatar_url": avatar_url,
        "language": language,
        "message": msg,
        "hint": hint,
        "send_label": send_label,
        
        "mentor_preview": {
            "name": name,
            "language": language,
            "voice": voice,
            "style": style,
            "specializations": specs,
            "avatar_id": avatar_id,
            "avatar_url": avatar_url,
        }
    })
