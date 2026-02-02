from tortoise import Tortoise
from models import user

async def init_db(DATABASE_URL):
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={"models": ["models.user"]}
    )
    await Tortoise.generate_schemas(safe=True)
