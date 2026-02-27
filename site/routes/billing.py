from quart import Blueprint, render_template, request, session, Response
from services.require_login import require_login
from models.user import User

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/billing', methods=['GET', 'POST'])
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
