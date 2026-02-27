from .auth import auth_bp
from .dashboard import dashboard_bp
from .course import course_bp
from .lesson import lesson_bp
from .account import account_bp
from .interview import interview_bp
from .utils_api import utils_bp
from .billing import billing_bp

blueprints = [auth_bp, dashboard_bp, course_bp, lesson_bp, account_bp, interview_bp, utils_bp, billing_bp]
