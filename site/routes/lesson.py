from quart import Blueprint, render_template, request, redirect, url_for, session, Response, jsonify
from services.require_login import require_login
import json
import re
from models.user import User  
from services.api_service import send_request_to_api
from services.transcription import transcribe_audio_with_prepare_data  



@lesson_bp.route('/lesson_call/<int:user_id>/<int:mentor_idx>/<int:lesson_id>', methods=['GET', 'POST'])



