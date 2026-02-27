from quart import Blueprint
from models.user import User
from services.require_login import require_login
from quart import Response
from quart import session
from quart import request
from quart import render_template



async def billing():
    user = await require_login()
    if isinstance(user, Response):
        return user
    user = await User.get(id=session['user_id'])

    message = ""
    if request.method == 'POST':
        form = await request.form
        selected_plan = form.get('plan')
        payment_method = form.get('method')

        message = f"Выбран план: {selected_plan}, способ оплаты: {payment_method}. Платёж обрабатывается..."

    return await render_template(
        'billing.html',
        user=user,
        message=message
    )


billing_bp = Blueprint('billing', __name__)
