from __future__ import annotations
from quart import Blueprint, request, session, render_template, redirect, url_for, jsonify
from models.user import User
from services.api_service import send_request_to_api

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

    user = await User.get_or_none(id=session_user_id)
    if not user:
        return redirect(url_for("auth.login"))

    courses = user.course_info if isinstance(user.course_info, list) else []
    course_idx = len(courses or [])

    return redirect(url_for("mentor_workspace.workspace", user_id=session_user_id, course_idx=course_idx))

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

    course_idx = request.args.get("course_idx", type=int)

    courses = user.course_info if isinstance(user.course_info, list) else []
    total = len(courses)

    if course_idx is None:
        course_idx = total

    mentor_data = None
    is_existing = 0 <= course_idx < total
    if is_existing:
        root = courses[course_idx] or {}
        mentor_data = {
            "course": root.get("course") or [],
            "mentor": root.get("mentor") or {},
            "course_settings": root.get("course_settings") or {},
        }

    return await render_template(
        "mentor_workspace.html",
        user=user,
        mentor_id=None,
        mentor_data=mentor_data,  
        lessons=[],
        is_new=not is_existing,
        avatar_options=AVATAR_OPTIONS,
        course_idx=course_idx,     
    )

@mentor_workspace.route('/mentor_workspace/<int:user_id>/chat', methods=['POST'])
async def mw_chat(user_id: int):
    if 'user_id' not in session or session['user_id'] != user_id:
        return jsonify({"error": "forbidden"}), 403

    user = await User.get(id=user_id)
    if not user:
        return jsonify({"error": "no user"}), 404

    data = await request.get_json()
    if not data:
        return jsonify({"error": "no json"}), 400

    course_idx = request.args.get("course_idx", type=int)
    if course_idx is None:
        course_idx = 0

    if not isinstance(user.course_info, list):
        user.course_info = []
    while len(user.course_info) <= course_idx:
        user.course_info.append({"course": [], "mentor": {}, "course_settings": {}})

    message = (data.get("message") or "").strip()
    state   = data.get("state") or {}
    is_intro = bool(data.get("intro"))

    conv_key = f"mw_conv_{user_id}_{course_idx}"
    conversation = session.get(conv_key, [])

    if not is_intro and message:
        conversation.append({"role": "user", "content": message})

    current_course = user.course_info[course_idx].get("course") or []

    mentor_prefs = {
        "name": state.get("name"),
        "language": state.get("language"),
        "style": state.get("style"),
        "voice": state.get("voice"),
        "specializations": state.get("specializations") or [],
        "avatar": state.get("avatar"),
    }

    payload = {
        "0_content": {
            "0_conversation": conversation,
            "1_user_info": user.user_info,
            "2_course_info": current_course,
            "3_mentor_prefs": mentor_prefs
        },
        "1_type": "course_creation"
    }

    response = await send_request_to_api(payload)

    if response.get("response"):
        conversation.append({"role": "manager", "content": response["response"]})

    if "course_info" in response:
        user.course_info[course_idx]["course"] = response["course_info"]
        user.course_info[course_idx]["mentor"] = mentor_prefs
        await User.filter(id=user.id).update(course_info=user.course_info)

    session[conv_key] = conversation

    return jsonify({
        "response": response.get("response"),
        "course_info": response.get("course_info")
    })

@mentor_workspace.route('/mentor_workspace/<int:user_id>/status', methods=['POST'])
async def mw_status_poll(user_id: int):
    if 'user_id' not in session or session['user_id'] != user_id:
        return jsonify({"error": "forbidden"}), 403

    user = await User.get(id=user_id)
    if not user:
        return jsonify({"error": "no user"}), 404

    data = await request.get_json()
    if not data:
        return jsonify({"error": "no json"}), 400

    course_idx = request.args.get("course_idx", type=int)
    if course_idx is None:
        course_idx = 0

    if not isinstance(user.course_info, list):
        user.course_info = []
    while len(user.course_info) <= course_idx:
        user.course_info.append({"course": [], "mentor": {}, "course_settings": {}})

    payload = data.get("status_payload")
    if not payload:
        return jsonify({"error": "no payload"}), 400

    response = await send_request_to_api(payload)

    state = data.get("state") or {}
    mentor_prefs = {
        "name": state.get("name"),
        "language": state.get("language"),
        "style": state.get("style"),
        "voice": state.get("voice"),
        "specializations": state.get("specializations") or [],
        "avatar": state.get("avatar"),
    }

    if "course_info" in response:
        user.course_info[course_idx]["course"] = response["course_info"]
        user.course_info[course_idx]["mentor"] = mentor_prefs
        await User.filter(id=user.id).update(course_info=user.course_info)

    return jsonify({
        "response": response.get("response"),
        "course_info": response.get("course_info")
    })

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

@mentor_workspace.route('/mentor_workspace/<int:user_id>/upsert_structure', methods=['POST'])
async def mw_upsert_structure(user_id: int):
    if 'user_id' not in session or session['user_id'] != user_id:
        return jsonify({"error": "forbidden"}), 403

    user = await User.get(id=user_id)
    if not user:
        return jsonify({"error": "no user"}), 404

    course_idx = request.args.get("course_idx", type=int)
    if course_idx is None:
        course_idx = 0

    data = await request.get_json()
    course_info = data.get("course_info")
    if not isinstance(course_info, list):
        return jsonify({"error": "bad course_info"}), 400

    if not isinstance(user.course_info, list):
        user.course_info = []
    while len(user.course_info) <= course_idx:
        user.course_info.append({"course": [], "mentor": {}, "course_settings": {}})

    user.course_info[course_idx]["course"] = course_info
    await User.filter(id=user.id).update(course_info=user.course_info)

    return jsonify({"ok": True, "course_info": course_info})

@mentor_workspace.route('/mentor_workspace/<int:user_id>/lesson', methods=['GET'])
async def open_lesson(user_id: int):
    
    if 'user_id' not in session or session['user_id'] != user_id:
        return redirect(url_for("auth.login"))

    course_idx = request.args.get("course_idx", type=int)
    topic_idx  = request.args.get("topic_idx",  type=int)
    lesson_idx = request.args.get("lesson_idx", type=int)

    if course_idx is None or topic_idx is None or lesson_idx is None:
        
        return redirect(url_for("mentor_workspace.workspace", user_id=user_id, course_idx=course_idx or 0))

    user = await User.get_or_none(id=user_id)
    if not user:
        return redirect(url_for("auth.login"))

    courses = user.course_info if isinstance(user.course_info, list) else []
    if not (0 <= course_idx < len(courses)):
        
        return redirect(url_for("mentor_workspace.workspace", user_id=user_id, course_idx=len(courses)))

    course_obj = courses[course_idx] or {}
    topics = course_obj.get("course") or []   

    if not (0 <= topic_idx < len(topics)):
        return redirect(url_for("mentor_workspace.workspace", user_id=user_id, course_idx=course_idx))

    topic_title = list(topics[topic_idx].keys())[0]
    lesson_list = topics[topic_idx].get(topic_title) or []

    if not (0 <= lesson_idx < len(lesson_list)):
        return redirect(url_for("mentor_workspace.workspace", user_id=user_id, course_idx=course_idx))

    lesson_title = lesson_list[lesson_idx]
    mentor = course_obj.get("mentor") or {}

    lesson_id = f"{course_idx}-{topic_idx}-{lesson_idx}"

    legacy = {
        "3_name": mentor.get("name") or "Mentor",
        "0_topic": topic_title,
        "5_categories": mentor.get("specializations") or [],
        
        "4_structure": [
            {"0_topic": t_title, "3_lessons": [{"name": l} for l in (topics[i][t_title])]}
            for i, t in enumerate(topics)
            for t_title in t.keys()
        ],
    }

    lesson_ctx = {
        "course_idx": course_idx,
        "topic_idx": topic_idx,
        "lesson_idx": lesson_idx,
        "lesson_id": lesson_id,
        "topic_title": topic_title,
        "lesson_title": lesson_title,
        "mentor": mentor,
        "course": topics,   
        "legacy": legacy,   
    }

    return redirect(url_for('lesson.lesson_call', user_id=user_id, mentor_idx=course_idx, lesson_id=lesson_id))
