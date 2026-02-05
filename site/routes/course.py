from quart import Blueprint, request, session, redirect, url_for, render_template, jsonify, Response
from models.user import User
from services.user_service import require_login
from services.api_service import send_request_to_api, get_empty_course_info
import json

course_bp = Blueprint("course", __name__)

@course_bp.route('/course_creation/<int:user_id>/<int:course_idx>', methods=['GET', 'POST'])
async def course_creation(user_id, course_idx):
    user = await require_login()
    if isinstance(user, Response):
        return user
    if not user.has_completed_interview:
        return await render_template('interview_modal.html')

    user = await User.get(id=user_id)
    if not user or user.id != session['user_id']:
        return "Доступ запрещен", 403

    if session.get("language") == "ru":
        start_message = request.args.get("start_message", "Привет! Это снова я, менеджер. Курс по какой теме тебя интересует?")
    else:
        start_message = request.args.get("start_message", "Hello! It's me again, the manager. What course topic are you interested in?")

    if start_message and not session.get('conversation'):
        session['conversation'] = [{"role": "manager", "content": start_message}]

    if request.method == 'POST':
        form = await request.form
        status_payload_raw = form.get('status_payload')
        if status_payload_raw:
            payload = json.loads(status_payload_raw)
            response = await send_request_to_api(payload)

            if "course_info" in response:
                user.course_info[course_idx]["course"] = response["course_info"]
                await User.filter(id=user.id).update(course_info=user.course_info)

            if response.get("response"):
                session['conversation'].append({"role": "manager", "content": response["response"]})

            return jsonify(response)
        else:
            conversation_text = form['conversation']
            conversation = session.get('conversation', [])
            conversation.append({"role": "user", "content": conversation_text})

            while len(user.course_info) <= course_idx:
                user.course_info.append({
                    "course": await get_empty_course_info(),
                    "course_settings": {}
                })
            course_info = user.course_info[course_idx]["course"]
            payload = {
                "0_content": {
                    "0_conversation": conversation,
                    "1_user_info": user.user_info,
                    "2_course_info": course_info
                },
                "1_type": "course_creation"
            }
            response = await send_request_to_api(payload)

            if "<GENERATION>" in response.get("status"):
                wait_message = {
                    "ru": "Генерация структуры курса займет 2–3 минуты. Пожалуйста, не закрывайте страницу.",
                    "en": "The course structure will take 2–3 minutes to generate. Please don’t close the page."
                }.get(session.get("language", "ru"))

                conversation.append({"role": "manager", "content": wait_message})
                session['conversation'] = conversation

                return jsonify({
                    "response": wait_message,
                    "status": response["status"],
                    "status_payload": json.dumps({
                        "0_content": {
                            "0_conversation": conversation,
                            "1_user_info": user.user_info,
                            "2_course_info": course_info,
                            "set_status": response["status"]
                        },
                        "1_type": "course_creation"
                    })
                })

            if "<END>" in response.get("status"):
                first_lesson = user.course_info[course_idx]["course"]["4_structure"][0]["3_lessons"][0]["name"]
                user.course_info[course_idx]["course_settings"] = {"lesson": first_lesson}
                await User.filter(id=user.id).update(course_info=user.course_info)

            if response.get("response"):
                conversation.append({"role": "manager", "content": response["response"]})
            session['conversation'] = conversation

            if "course_info" in response:
                user.course_info[course_idx]["course"] = response["course_info"]
                await User.filter(id=user.id).update(course_info=user.course_info)

            return jsonify(response)

    session['conversation'] = []
    while len(user.course_info) <= course_idx:
        user.course_info.append({
            "course": await get_empty_course_info(),
            "course_settings": {}
        })
    await User.filter(id=user.id).update(course_info=user.course_info)

    course_name = user.course_info[course_idx]["course"].get("3_name", "")
    return await render_template('course_creation.html', user=user, course_idx=course_idx, username=user.username, course_name=course_name, start_message=start_message)

@course_bp.route('/course_select/<int:user_id>/<int:course_idx>', methods=['GET', 'POST'])
async def course_select(user_id, course_idx):
    user = await require_login()
    if isinstance(user, Response):
        return user
    user = await User.get(id=user_id)
    if not user or user.id != session['user_id']:
        return "Доступ запрещен", 403

    if course_idx >= len(user.course_info):
        return "Курс не найден", 404

    course = user.course_info[course_idx]["course"]

    if "4_structure" not in course or not course["4_structure"]:
        return redirect(url_for('course.course_creation', user_id=user_id, course_idx=course_idx))

    if "lesson" not in user.course_info[course_idx]["course_settings"]:
        try:
            first_lesson = course["4_structure"][0]["3_lessons"][0]["name"]
            user.course_info[course_idx]["course_settings"]["lesson"] = first_lesson
            await User.filter(id=user.id).update(course_info=user.course_info)
        except (IndexError, KeyError):
            pass

    for topic in course["4_structure"]:
        for i, lesson in enumerate(topic["3_lessons"]):
            if "paid" not in lesson:
                lesson["paid"] = (topic == course["4_structure"][0] and i == 0)
    await User.filter(id=user.id).update(course_info=user.course_info)

    next_lesson = user.course_info[course_idx]["course_settings"].get("lesson")
    next_lesson_paid = False
    if next_lesson:
        for topic in course["4_structure"]:
            for lesson in topic["3_lessons"]:
                if lesson["name"] == next_lesson:
                    next_lesson_paid = lesson.get("paid", False)
                    break
            if next_lesson_paid:
                break

    if request.method == 'POST':
        form = await request.form
        action = form.get('action')
        if action == 'lesson':
            if next_lesson_paid:
                return redirect(url_for('lesson_call', user_id=user_id, course_idx=course_idx))
            elif user.credits > 0:
                user.credits -= 1
                await User.filter(id=user.id).update(credits=user.credits)
                for topic in course["4_structure"]:
                    for lesson in topic["3_lessons"]:
                        if lesson["name"] == next_lesson:
                            lesson["paid"] = True
                            break
                await User.filter(id=user.id).update(course_info=user.course_info)
                return redirect(url_for('lesson_call', user_id=user_id, course_idx=course_idx))
            else:
                total_lessons = sum(len(t["3_lessons"]) for t in course["4_structure"])
                completed_lessons = 0
                found = False
                for topic in course["4_structure"]:
                    for lesson in topic["3_lessons"]:
                        if lesson["name"] == next_lesson:
                            found = True
                        if not found:
                            completed_lessons += 1
                progress = (completed_lessons / total_lessons) * 100
                return await render_template(
                    'course_select.html',
                    user=user, course=course, course_idx=course_idx,
                    username=user.username, progress=progress,
                    course_id=course_idx, next_lesson=next_lesson,
                    next_lesson_paid=next_lesson_paid,
                    insufficient_credits=True
                )
        elif action == 'edit':
            return redirect(url_for('course.course_edit', user_id=user_id, course_idx=course_idx))
        elif action == 'settings':
            return redirect(url_for('course_settings', user_id=user_id, course_idx=course_idx))

    total = sum(len(topic["3_lessons"]) for topic in course["4_structure"])
    completed = 0
    flag = False
    for topic in course["4_structure"]:
        for lesson in topic["3_lessons"]:
            if lesson["name"] == next_lesson:
                flag = True
            if not flag:
                completed += 1
    progress = (completed / total * 100) if total else 0

    return await render_template(
        'course_select.html',
        user=user, course=course, course_idx=course_idx,
        username=user.username, progress=progress,
        course_id=course_idx, next_lesson=next_lesson,
        next_lesson_paid=next_lesson_paid
    )

@course_bp.route('/course_edit/<int:user_id>/<int:course_idx>', methods=['GET', 'POST'])
async def course_edit(user_id, course_idx):
    user = await require_login()
    if isinstance(user, Response):
        return user
    user = await User.get(id=user_id)

    if not user or user.id != session['user_id']:
        return "Доступ запрещен", 403

    if request.method == 'POST':
        form = await request.form
        conversation_text = form['conversation']
        conversation = session.get('conversation', [])
        conversation.append({"role": "user", "content": conversation_text})

        if len(user.course_info) <= course_idx:
            return "Курс с указанным индексом не найден.", 404

        course_info = user.course_info[course_idx]["course"]

        payload = {
            "0_content": {
                "0_conversation": conversation,
                "1_user_info": user.user_info,
                "2_course_info": course_info
            },
            "1_type": "course_edit"
        }
        response = await send_request_to_api(payload)

        if response.get("response"):
            conversation.append({"role": "manager", "content": response["response"]})
        session['conversation'] = conversation

        if "course_info" in response:
            user.course_info[course_idx]["course"] = response["course_info"]
            await User.filter(id=user.id).update(course_info=user.course_info)

        return jsonify(response)

    session['conversation'] = []
    course_name = user.course_info[course_idx]["course"].get("3_name", "")
    return await render_template(
        'course_edit.html',
        user=user, course_idx=course_idx,
        username=user.username, course_name=course_name
    )

@course_bp.route('/delete_course/<int:course_idx>', methods=['POST'])
async def delete_course(course_idx):
    user = await require_login()
    if isinstance(user, Response):
        return user

    if course_idx < 0 or course_idx >= len(user.course_info):
        return "Course not found", 404

    user.course_info.pop(course_idx)
    await user.save()

    return redirect(url_for('dashboard.library'))
