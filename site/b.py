import asyncio
from tortoise import Tortoise, fields
from tortoise.models import Model
import sqlite3

DATABASE_URL = "sqlite://neuromentor.db"
DB_FILE = "neuromentor.db"  

class User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=80, unique=True)
    password = fields.CharField(max_length=120)
    user_info = fields.JSONField(default={})
    course_info = fields.JSONField(default=[])
    has_completed_interview = fields.BooleanField(default=False)
    recommendations = fields.JSONField(default=[])
    credits = fields.IntField(default=0)  

async def add_column():
                                    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(user);")
    columns = [col[1] for col in cursor.fetchall()]                              

    if "credits" not in columns:
        print("Добавляем колонку 'credits' в таблицу user...")
        cursor.execute("ALTER TABLE user ADD COLUMN credits INTEGER DEFAULT 0;")
        conn.commit()
    else:
        print("Колонка 'credits' уже существует, пропускаем добавление.")

    conn.close()                                

    await Tortoise.init(db_url=DATABASE_URL, modules={"models": ["__main__"]})
    await Tortoise.generate_schemas()

    users = await User.all().values("id", "credits")

    for user in users:
        if user["credits"] is None:
            await User.filter(id=user["id"]).update(credits=0)

    print("Колонка 'credits' успешно добавлена и обновлена для всех пользователей.")
    await Tortoise.close_connections()

asyncio.run(add_column())
