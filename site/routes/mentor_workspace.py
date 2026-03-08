from __future__ import annotations
from quart import Blueprint, request, session, render_template, redirect, url_for, jsonify
from models.user import User

mentor_workspace = Blueprint("mentor_workspace", __name__)

SUPPORTED_LANGS = {"ru", "en"}
SUPPORTED_VOICES = {
    
    "ru": ["anna", "mikhail", "alena"],
    "en": ["jane", "john", "emma"],
}

AVATAR_OPTIONS = [
    {"id": "bot_blue", "url": "https://img.icons8.com/color/96/bot.png", "label": "Bot Blue"},
    {"id": "mentor_male", "url": "https://img.icons8.com/color/96/teacher.png", "label": "Mentor Male"},
    {"id": "mentor_female", "url": "https://img.icons8.com/color/96/training.png", "label": "Mentor Female"},
    {"id": "owl", "url": "https://img.icons8.com/color/96/owl.png", "label": "Owl"},
]

@mentor_workspace.route("/mentor_workspace", methods=["GET"])
@mentor_workspace.route("/mentor_workspace/", methods=["GET"])
async def workspace_entry():
    session_user_id = session.get("user_id")
    if not session_user_id:
        return redirect(url_for("auth.login"))
    return redirect(url_for("mentor_workspace.workspace", user_id=session_user_id))

@mentor_workspace.route("/mentor_workspace/<int:user_id>", methods=["GET"])
@mentor_workspace.route("/mentor_workspace/<int:user_id>/", methods=["GET"])
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

@mentor_workspace.route("/mentor_workspace/<int:user_id>/avatar_options", methods=["GET"])
async def get_avatar_options(user_id: int):
    
    session_user_id = session.get("user_id")
    if not session_user_id or session_user_id != user_id:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    return jsonify({"ok": True, "avatars": AVATAR_OPTIONS})

@mentor_workspace.route("/mentor_workspace/<int:user_id>/validate", methods=["POST"])
async def validate_fields(user_id: int):
    session_user_id = session.get("user_id")
    if not session_user_id or session_user_id != user_id:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    payload = await request.get_json(force=True, silent=True) or {}
    name: str = (payload.get("name") or "").strip()
    specs = payload.get("specializations") or []  
    language: str = (payload.get("language") or "").strip().lower()
    style: str = (payload.get("style") or "").strip()
    voice: str = (payload.get("voice") or "").strip().lower()
    avatar_id: str = (payload.get("avatar_id") or "").strip()

    errors = {}

    if not name or len(name) < 2:
        errors["name"] = "Имя слишком короткое." if language == "ru" else "Name is too short."

    if not isinstance(specs, list) or not any((s or "").strip() for s in specs):
        errors["specializations"] = "Добавьте хотя бы одну специализацию." if language == "ru"            else "Add at least one specialization."
    else:
        
        specs = [str(s).strip() for s in specs if str(s).strip()]

    if language not in SUPPORTED_LANGS:
        errors["language"] = "Поддерживаются только RU и EN." if language == "ru" else "Only RU and EN are supported."

    if language in SUPPORTED_VOICES and voice not in SUPPORTED_VOICES[language]:
        errors["voice"] = ("Выберите голос из списка: " + ", ".join(SUPPORTED_VOICES[language]))            if language == "ru" else ("Choose a voice: " + ", ".join(SUPPORTED_VOICES[language]))

    if style and len(style) < 3:
        errors["style"] = "Слишком коротко." if language == "ru" else "Too short."

    if avatar_id and avatar_id not in {a["id"] for a in AVATAR_OPTIONS}:
        errors["avatar_id"] = "Некорректный аватар." if language == "ru" else "Invalid avatar."

    ready = len(errors) == 0
    return jsonify({"ok": True, "ready": ready, "errors": errors})

@mentor_workspace.route("/mentor_workspace/<int:user_id>/intro", methods=["POST"])
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

@mentor_workspace.route("/mentor_workspace/<int:user_id>/save_draft", methods=["POST"])
async def save_draft(user_id: int):
    session_user_id = session.get("user_id")
    if not session_user_id or session_user_id != user_id:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    payload = await request.get_json(force=True, silent=True) or {}
    
    session.setdefault("mentor_draft", {})
    session["mentor_draft"][str(user_id)] = payload
    
    return jsonify({"ok": True})
