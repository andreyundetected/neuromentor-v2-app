from quart import Blueprint, render_template, request, redirect, url_for, session, Response, jsonify
from services.require_login import require_login
import json
import re
from models.user import User  
from services.api_service import send_request_to_api
from services.transcription import transcribe_audio_with_prepare_data  



@lesson_bp.route('/lesson_call/<int:user_id>/<int:mentor_idx>/<int:lesson_id>', methods=['GET', 'POST'])
async def lesson_call(user_id, mentor_idx, lesson_id):
    user = await require_login()
    if isinstance(user, Response):
        return user
    user = await User.get(id=user_id)

    if not user or user.id != session['user_id']:
        return "Доступ запрещен", 403

    courses = user.course_info if isinstance(user.course_info, list) else []
    if not (0 <= mentor_idx < len(courses)):
        return redirect(url_for('dashboard.library'))

    course_obj   = courses[mentor_idx] or {}
    course_struct = course_obj.get("course") or []          
    course_sets   = course_obj.get("course_settings") or {}

    flat = _flatten_course(course_struct)
    if not (0 <= lesson_id < len(flat)):
        
        return redirect(url_for('mentor_workspace.workspace', user_id=user_id, mentor_idx=mentor_idx))

    topic_idx, lesson_idx, topic_title, lesson_title = flat[lesson_id]

    course_sets["lesson"] = lesson_title
    user.course_info[mentor_idx]["course_settings"] = course_sets
    await User.filter(id=user.id).update(course_info=user.course_info)

    paid_status = True

    if not paid_status:
        
        return redirect(url_for('mentor_workspace.workspace', user_id=user_id, course_idx=mentor_idx))

    conversation_chat = session.get('conversation_chat', [])
    conversation_call = session.get('conversation_call', [])
    conversation = session.get('conversation', [])
    
    with open("conversation_chat.json", "r", encoding="utf-8") as f:
        conversation_chat = json.load(f)
    with open("conversation_call.json", "r", encoding="utf-8") as f:
        conversation_call = json.load(f)
    with open("conversation.json", "r", encoding="utf-8") as f:
        conversation = json.load(f)
    
    lesson_plan = session.get('lesson_plan', "")
    lesson_blocks = session.get('lesson_plan', "").split("<BLOCKS>")[-1].split("</BLOCKS>")[0].split("</block>")
    presentation_history = session.get('presentation_history', "")
    progress = session.get('progress', 0)

    if request.method == 'POST':

        form = await request.form
        files = await request.files
        
        print("[DEBUG] Full POST form:")
        for key, value in form.items():
            print(f"    {key} = {value}")

        print("[DEBUG] POST files:")
        for key, file in files.items():
            print(f"    {key} = {file.filename}, content_type: {file.content_type}, size: {len(file.read())} bytes")
            file.seek(0)  

        print("[DEBUG] Field 'conversation':", form.get("conversation"))
        print("[DEBUG] Field 'response_mode':", form.get("response_mode"))

        form = await request.form
        response_mode = form.get("response_mode", "audio")
        
        conversation_text = form.get('conversation', '').strip()
        if conversation_text:
            
            conversation_chat.append({"role": "user", "content": conversation_text})
            conversation.append({"type": "CHAT", "role": "user", "content": conversation_text})
        import io
        from pydub import AudioSegment
        import os

        files = await request.files
        audio_file = files.get("audio")  
        transcript_result = None

        if audio_file:
            print("[LESSON_CALL] Received audio file:", audio_file.filename)

            audio_bytes = io.BytesIO(audio_file.read())  
            audio_bytes.seek(0)  

            temp_audio_path = "temp_audio.webm"
            with open(temp_audio_path, "wb") as file:
                file.write(audio_bytes.getvalue())
            audio = AudioSegment.from_file(temp_audio_path, format="webm")
            
            try:
                transcript_result = transcribe_audio_with_prepare_data(audio) 
                os.remove(temp_audio_path)
                print("[LESSON_CALL] Transcription:", transcript_result)
                conversation_call.append({"role": "user VOICE", "content": transcript_result})
                conversation.append({"type": "AUDIO TRANSCRIPTION", "role": "user", "content": transcript_result})
            except Exception as e:
                print("[LESSON_CALL] Error transcribing audio:", e)

        if len(user.course_info) < mentor_idx:
            return "Course not found", 404

        if lesson_plan == "" and False:
            payload = {
                "0_content": {
                    "1_user_info": user.user_info,
                    "2_course_info": user.course_info[mentor_idx]["course"],
                    "3_lesson_topic": topic_title,
                },
                "1_type": "lesson_plan"
            }

            response_api = await send_request_to_api(payload)
            lesson_plan = response_api.get("lesson_plan", "")
            lesson_blocks = response_api.get("lesson_plan", "").split("<BLOCKS>")[-1].split("</BLOCKS>")[0].split("</block>")
            print("[LESSON_CALL] API lesson_plan response:", response_api)

        payload = {
            "0_content": {
                "0_conversation_chat": conversation_chat,   
                "0_conversation_call": conversation_call,   
                "0_conversation": conversation,   
                "1_user_info": user.user_info,
                "2_course_info": user.course_info[mentor_idx]["course"],
                "2_mentor_prefs": user.course_info[mentor_idx]["mentor"],
                "3_lesson_topic": topic_title,
                "4_progress": progress,
                "5_presentation_history": presentation_history,
                "6_lesson_plan": lesson_plan,
                "6_lesson_blocks": lesson_blocks,
                "7_lesson_info": {"topic": topic_title, "lesson_name": lesson_title},
            },
            "1_type": "lesson_call"
        }

        response_api = await send_request_to_api(payload)
        print("[LESSON_CALL] API response:", response_api)

        response_chat = response_api.get("response_chat", "")
        response_call = response_api.get("response_call", None)
        response_call_transcription = response_api.get("response_call_transcription", "")
        response_type = response_api.get("response_type", "")
        status = response_api.get("status", "<OK>")
        presentation_description = response_api.get("presentation_description", "")
        new_progress = response_api.get("progress")
        presentation_image = response_api.get("presentation_image")
        block_tag = response_api.get("block_tag")

        if response_chat:
            if re.sub(r"[^a-zA-Zа-яА-Я]", "", response_chat).lower() == "none":
                response_chat = None
            conversation_chat.append({"role": f"teacher CHAT {response_type}", "content": response_chat, "block_tag": block_tag})
            conversation.append({"type": f"CHAT {response_type}", "role": "teacher", "content": response_chat, "block_tag": block_tag})

        if response_call_transcription:
            conversation_call.append({"role": f"teacher VOICE {response_type}", "content": response_call_transcription, "block_tag": block_tag})
            conversation.append({"type": f"AUDIO TRANSCRIPTION {response_type}", "role": "teacher", "content": response_call_transcription, "block_tag": block_tag})

        if presentation_description:
            presentation_history += (presentation_description + "\n\n")
        
        if new_progress is not None:
            progress = float(new_progress)

        if status == "<END>":
            print("[LESSON_CALL] Lesson ended according to API response")

        session['conversation_chat'] = conversation_chat
        session['conversation_call'] = conversation_call
        session['conversation'] = conversation
        session['progress'] = progress
        session['lesson_plan'] = lesson_plan
        session['presentation_history'] = presentation_history
    
        with open("conversation_chat.json", "w", encoding="utf-8") as f:
            json.dump(conversation_chat, f, ensure_ascii=False, indent=2)
        with open("conversation_call.json", "w", encoding="utf-8") as f:
            json.dump(conversation_call, f, ensure_ascii=False, indent=2)
        with open("conversation.json", "w", encoding="utf-8") as f:
            json.dump(conversation, f, ensure_ascii=False, indent=2)
    
        response_data = {
            "response_chat": response_chat,               
            "response_call": response_call,        
            "audio_input_transcription": transcript_result,
            "response_call_transcription": response_call_transcription,  
            "response_type": response_type,
            "status": status,
            "progress": progress,
            "presentation_image": presentation_image
        }
        return jsonify(response_data)

    session['conversation_chat'] = []
    session['conversation_call'] = []
    session['conversation'] = []
    
    with open("conversation_chat.json", "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)
    with open("conversation_call.json", "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)
    with open("conversation.json", "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)
    
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


