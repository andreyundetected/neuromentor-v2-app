from services.recommendations import generate_default_recommendations
from models.user import User
from services.user_service import require_login
from collections import Counter
from quart import Response
from quart import session
from quart import url_for
from quart import render_template
from quart import Blueprint


dashboard_bp = Blueprint('dashboard', __name__)


async def library():
    user = await require_login()
    if isinstance(user, Response):
        return user

    if not user.recommendations or True:
        user.recommendations = generate_default_recommendations(session.get("language"))
        await User.filter(id=user.id).update(recommendations=user.recommendations)

    if not user.course_info:
        user.course_info = []

    courses_with_indices = [{"index": idx, "course": course} for idx, course in enumerate(user.course_info)]

    categories = []
    for course_wrapper in user.course_info:
        categories.extend(course_wrapper["course"].get("5_categories", []))
    category_counts = Counter(categories)
    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)

    new_course_index = len(user.course_info)
    new_course_url = url_for('course_creation', user_id=user.id, course_idx=new_course_index)

    return await render_template(
        'library.html',
        user=user,
        courses_with_indices=courses_with_indices,
        new_course_url=new_course_url,
        sorted_categories=sorted_categories, 
        username=user.username,
        enumerate=enumerate,
        show_interview_modal=not user.has_completed_interview
    )
