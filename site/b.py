

class User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=80, unique=True)
    password = fields.CharField(max_length=120)
    user_info = fields.JSONField(default={})
    course_info = fields.JSONField(default=[])
    has_completed_interview = fields.BooleanField(default=False)
    recommendations = fields.JSONField(default=[])
    credits = fields.IntField(default=0)


DB_FILE = "neuromentor.db"


DATABASE_URL = "sqlite://neuromentor.db"
