from quart import Blueprint, render_template, request, redirect, url_for, session, Response
from collections import Counter
from services.require_login import require_login
from models.user import User
from services.recommendations import generate_default_recommendations  

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
async def index():
    if "user_id" in session:
        user = await User.get(id=session["user_id"])
        if user:
            session["language"] = user.user_info.get("language", "ru")
            return redirect(url_for("dashboard.library"))
    return redirect(url_for("auth.login"))

@dashboard_bp.route('/library')
async def library():
    user = await require_login()
    if isinstance(user, Response):
        return user

    if not user.recommendations or True:
        user.recommendations = generate_default_recommendations(session.get("language"))
        await User.filter(id=user.id).update(recommendations=user.recommendations)

    if not user.courses_info:
        user.courses_info = []

    courses_with_indices = [{"index": idx, "course": course} for idx, course in enumerate(user.courses_info)]

    categories = []
    for course_wrapper in user.courses_info:
        categories.extend(course_wrapper["mentor"].get("specializations", []))
    category_counts = Counter(categories)
    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)

    new_course_index = len(user.courses_info)
    new_course_url = url_for('course.course_creation', user_id=user.id, course_idx=new_course_index)

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

@dashboard_bp.route('/delete_course/<int:course_idx>', methods=['POST'])
async def delete_course(course_idx):
    user = await require_login()
    if isinstance(user, Response):
        return user

    if course_idx < 0 or course_idx >= len(user.courses_info):
        return "Course not found", 404

    user.courses_info.pop(course_idx)
    await user.save()

    return redirect(url_for('dashboard.library'))
