from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import User, Book, Order, Category, Review, UserActivity
from forms import UserForm, CategoryForm, BookForm
from extensions import db
from utils.activity_logger import log_user_activity
from utils.mailer import send_order_status_email
from werkzeug.security import generate_password_hash
from functools import wraps

admin = Blueprint('admin', __name__, url_prefix='/admin')

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.can(permission):
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@admin.route('/dashboard')
@permission_required('manage_books')
def dashboard():
    books = Book.query.all()
    orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    categories = Category.query.all()
    return render_template('admin/dashboard.html', 
                         books=books,
                         orders=orders,
                         categories=categories)

@admin.route('/update_order_status/<int:order_id>', methods=['POST'])
@permission_required('manage_orders')
def update_order_status(order_id):
    try:
        data = request.get_json()
        order = Order.query.get_or_404(order_id)
        order.status = data['status']
        db.session.commit()
        
        send_order_status_email(order.user.email, order.id, order.status, order.items)
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/update_shipping_info/<int:order_id>', methods=['POST'])
@permission_required('manage_orders')
def update_shipping_info(order_id):
    try:
        data = request.get_json()
        order = Order.query.get_or_404(order_id)
        
        order.carrier = data.get('carrier')
        order.tracking_number = data.get('tracking_number')
        order.shipping_date = datetime.fromisoformat(data.get('shipping_date')) if data.get('shipping_date') else None
        order.shipping_address = data.get('shipping_address')
        
        db.session.commit()
        
        log_user_activity(current_user, 'shipping_update', 
                         f'Updated shipping info for order #{order.id}')
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})
