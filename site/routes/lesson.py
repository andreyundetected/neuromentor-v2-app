from quart import Blueprint
from quart import Blueprint, render_template, request, redirect, url_for, session, Response, jsonify
from services.require_login import require_login
import json
import re

from models.user import User  # если перенесешь заглушки

from services.api_service import send_request_to_api
from services.transcription import transcribe_audio_with_prepare_data  # если перенесешь заглушки

lesson_bp = Blueprint('lesson', __name__)

@lesson_bp.route('/lesson_call/<int:user_id>/<int:mentor_idx>/<int:lesson_id>', methods=['GET', 'POST'])
async def lesson_call(user_id, mentor_idx, lesson_id):
    user = await require_login()
    if isinstance(user, Response):
        return user
    user = await User.get(id=user_id)

    # доступ только владельцу
    if not user or user.id != session['user_id']:
        return "Доступ запрещен", 403

    # корректный индекс курса
    courses = user.course_info if isinstance(user.course_info, list) else []
    if not (0 <= mentor_idx < len(courses)):
        return redirect(url_for('dashboard.library'))

    course_obj   = courses[mentor_idx] or {}
    course_struct = course_obj.get("course") or []          # НОВАЯ структура
    course_sets   = course_obj.get("course_settings") or {}

    flat = _flatten_course(course_struct)
    if not (0 <= lesson_id < len(flat)):
        # неверный id -> на воркспейс выбранного курса
        return redirect(url_for('mentor_workspace.workspace', user_id=user_id, mentor_idx=mentor_idx))

    topic_idx, lesson_idx, topic_title, lesson_title = flat[lesson_id]

    course_sets["lesson"] = lesson_title
    user.course_info[mentor_idx]["course_settings"] = course_sets
    await User.filter(id=user.id).update(course_info=user.course_info)

    # Проверяем статус оплаты текущего урока.
    """paid_status = False
    for topic in user.course_info[mentor_idx]["course"]:
        for lessons in topic.values():
            for lesson in lessons:
            if lesson["name"] == topic_title:
                paid_status = lesson.get("paid", False)
                break
        if paid_status:
            break"""
    paid_status = True

    if not paid_status:
        # Если урок не оплачен, перенаправляем пользователя обратно на страницу выбора курса.
        return redirect(url_for('mentor_workspace.workspace', user_id=user_id, course_idx=mentor_idx))

    # conversation_chat = для текстовых сообщений
    # conversation_call = для транскрипций аудио
    conversation_chat = session.get('conversation_chat', [])
    conversation_call = session.get('conversation_call', [])
    conversation = session.get('conversation', [])
    ##########################временный пиздец
    with open("conversation_chat.json", "r", encoding="utf-8") as f:
        conversation_chat = json.load(f)
    with open("conversation_call.json", "r", encoding="utf-8") as f:
        conversation_call = json.load(f)
    with open("conversation.json", "r", encoding="utf-8") as f:
        conversation = json.load(f)
    ##########################временный пиздец

    lesson_plan = session.get('lesson_plan', "")
    lesson_blocks = session.get('lesson_plan', "").split("<BLOCKS>")[-1].split("</BLOCKS>")[0].split("</block>")
    presentation_history = session.get('presentation_history', "")
    progress = session.get('progress', 0)
    conspectus = session.get('conspectus', "")

    if request.method == 'POST':

        form = await request.form
        files = await request.files
        
        # === [DEBUG POST] ===
        print("[DEBUG] Full POST form:")
        for key, value in form.items():
            print(f"    {key} = {value}")

        print("[DEBUG] POST files:")
        for key, file in files.items():
            print(f"    {key} = {file.filename}, content_type: {file.content_type}, size: {len(file.read())} bytes")
            file.seek(0)  # не забудь, иначе потом файл будет пуст

        print("[DEBUG] Field 'conversation':", form.get("conversation"))
        print("[DEBUG] Field 'response_mode':", form.get("response_mode"))

        form = await request.form
        response_mode = form.get("response_mode", "audio")
        # 1) Обработка текстового поля (если есть)
        conversation_text = form.get('conversation', '').strip()
        if conversation_text:
            # Добавляем в чат
            conversation_chat.append({"role": "user", "content": conversation_text})
            conversation.append({"type": "CHAT", "role": "user", "content": conversation_text})
        import io
        from pydub import AudioSegment
        import os

        # 2) Обработка аудио (если есть)
        files = await request.files
        audio_file = files.get("audio")  # Получаем файл
        transcript_result = None

        if audio_file:
            print("[LESSON_CALL] Received audio file:", audio_file.filename)

            # Читаем файл в BytesIO
            audio_bytes = io.BytesIO(audio_file.read())  
            audio_bytes.seek(0)  # Важно! Перемещаем указатель в начало

            # Сохраняем файл на диск (для OpenAI API)
            temp_audio_path = "temp_audio.webm"
            with open(temp_audio_path, "wb") as file:
                file.write(audio_bytes.getvalue())
            audio = AudioSegment.from_file(temp_audio_path, format="webm")
            # Конвертация в WAV перед транскрипцией
            try:
                transcript_result = transcribe_audio_with_prepare_data(audio) 
                os.remove(temp_audio_path)
                print("[LESSON_CALL] Transcription:", transcript_result)
                conversation_call.append({"role": "user VOICE", "content": transcript_result})
                conversation.append({"type": "AUDIO TRANSCRIPTION", "role": "user", "content": transcript_result})
            except Exception as e:
                print("[LESSON_CALL] Error transcribing audio:", e)

        # 3) Проверки по mentor_idx
        if len(user.course_info) < mentor_idx:
            return "Course not found", 404
##################################
        if lesson_plan == "" and False:
            payload = {
                "0_content": {
                    "1_user_info": user.user_info,
                    "2_course_info": user.course_info[mentor_idx]["course"],
                    "3_lesson_topic": topic_title,
                },
                "1_type": "lesson_plan"
            }

            # Отправляем в API
            response_api = await send_request_to_api(payload)
            lesson_plan = response_api.get("lesson_plan", "")
            lesson_blocks = response_api.get("lesson_plan", "").split("<BLOCKS>")[-1].split("</BLOCKS>")[0].split("</block>")
            print("[LESSON_CALL] API lesson_plan response:", response_api)

        # 4) Формируем payload для внешнего API
        payload = {
            "0_content": {
                "0_conversation_chat": conversation_chat,   # основной чат (текст)
                "0_conversation_call": conversation_call,   # транскрипционный чат (аудио)
                "0_conversation": conversation,   # общий чат с хронологией сообщений
                "1_user_info": user.user_info,
                "2_course_info": user.course_info[mentor_idx]["course"],
                "2_mentor_prefs": user.course_info[mentor_idx]["mentor"],
                "3_conspectus": conspectus,
                "3_lesson_topic": topic_title,
                "4_progress": progress,
                "5_presentation_history": presentation_history,
                "6_lesson_plan": lesson_plan,
                "6_lesson_blocks": lesson_blocks,
                "7_lesson_info": {"topic": topic_title, "lesson_name": lesson_title},
            },
            "1_type": "lesson_call"
        }
[{'Арифметика': ['Основы чисел', 'Основные операции', 'Приоритет операций', 'Работа с дробями']}, {'Алгебра': ['Основы алгебры', 'Решение уравнений', 'Работа с графиками', 'Функции']}, {'Геометрия': ['Основы геометрии', 'Работа с углами', 'Работа с треугольниками', 'Основы стереометрии']}, {'Анализ': ['Основы анализа', 'Работа с пределами', 'Работа с производными', 'Работа с интегралами']}, {'Дифференциальные уравнения': ['Определение и классификация', 'Основные методы решения', 'Практические задачи', 'Применение дифференциальных уравнений в реальных задачах']}, {'Кулинарные рецепты': ['Ингредиенты', 'Приготовление начинки', 'Приготовление теста', 'Сборка и выпекание пирога']}]
        # Отправляем в API
        response_api = await send_request_to_api(payload)
        print("[LESSON_CALL] API response:", response_api)

        # Парсим нужные поля
        # Пример ответа:
        # {
        #   "response": "Teacher says hi",
        #   "response_call": "...(Base64 MP3)...",
        #   "response_call_transcription": "Teacher's voice text",
        #   "response_type": "text" или "voice",
        #   "status": "<END>" или "<OK>",
        #   "progress": 30.0
        # }
        response_chat = response_api.get("response_chat", "")
        response_call = response_api.get("response_call", None)
        response_call_transcription = response_api.get("response_call_transcription", "")
        response_type = response_api.get("response_type", "")
        status = response_api.get("status", "<OK>")
        presentation_description = response_api.get("presentation_description", "")
        new_progress = response_api.get("progress")
        presentation_image = response_api.get("presentation_image")
        block_tag = response_api.get("block_tag")

        # Если есть response_chat -> добавляем в chat
        if response_chat:
            conspectus += response_chat + "\n\n"

        # Если есть response_call_transcription -> добавляем в call
        if response_call_transcription:
            conversation_call.append({"role": f"teacher VOICE {response_type}", "content": response_call_transcription, "block_tag": block_tag})
            conversation.append({"type": f"AUDIO TRANSCRIPTION {response_type}", "role": "teacher", "content": response_call_transcription, "block_tag": block_tag})

        if presentation_description:
            presentation_history += (presentation_description + "\n\n")
        # Обновляем прогресс
        if new_progress is not None:
            progress = float(new_progress)

        # Если <END>, можно что-то сделать (напр. автопереход на другой урок)
        if status == "<END>":
            print("[LESSON_CALL] Lesson ended according to API response")

        # 5) Сохраняем всё в session
        session['conversation_chat'] = conversation_chat
        session['conversation_call'] = conversation_call
        session['conversation'] = conversation
        session['progress'] = progress
        session['lesson_plan'] = lesson_plan
        session['presentation_history'] = presentation_history
        session['conspectus'] = conspectus
    ##########################временный пиздец
        with open("conversation_chat.json", "w", encoding="utf-8") as f:
            json.dump(conversation_chat, f, ensure_ascii=False, indent=2)
        with open("conversation_call.json", "w", encoding="utf-8") as f:
            json.dump(conversation_call, f, ensure_ascii=False, indent=2)
        with open("conversation.json", "w", encoding="utf-8") as f:
            json.dump(conversation, f, ensure_ascii=False, indent=2)
    ##########################временный пиздец

        # 6) Формируем JSON-ответ клиенту
        response_data = {
            "response_chat": response_chat,               # текст для основного чата
            "response_call": response_call,        # base64 MP3
            "audio_input_transcription": transcript_result,
            "response_call_transcription": response_call_transcription,  # для транскрипционного чата
            "response_type": response_type,
            "status": status,
            "progress": progress,
            "presentation_image": presentation_image
        }
        return jsonify(response_data)

    # GET-запрос -> сбрасываем разговоры и прогресс
    session['conversation_chat'] = []
    session['conversation_call'] = []
    session['conversation'] = []
    ##########################временный пиздец
    with open("conversation_chat.json", "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)
    with open("conversation_call.json", "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)
    with open("conversation.json", "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)
    ##########################временный пиздец

    session['lesson_plan'] = ""
    session['progress'] = 0
    lesson_title = user.course_info[mentor_idx]["course_settings"].get("lesson", "")
    return await render_template(
        'lesson_call.html',
        user=user,
        mentor_idx=mentor_idx,
        lesson_id=lesson_id,
        username=user.username,
        lesson_title=lesson_title,
        transcript_history=conversation_call
    )

def _flatten_course(course_struct):
    """
    [{"Topic A": ["L1","L2"]}, {"Topic B":["L3"]}] ->
    [(t_idx, l_idx, topic_title, lesson_title), ...]
    """
    out = []
    for t_idx, t in enumerate(course_struct or []):
        topic_title = next(iter(t.keys()), None)
        if topic_title is None:
            continue
        lessons = t.get(topic_title) or []
        for l_idx, title in enumerate(lessons):
            out.append((t_idx, l_idx, topic_title, title))
    return out


lesson_bp = Blueprint('lesson', __name__)
