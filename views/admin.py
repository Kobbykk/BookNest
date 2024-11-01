from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import User, Book, Order, Category, Review, UserActivity
from forms import UserForm, CategoryForm, BookForm
from extensions import db
from utils.activity_logger import log_user_activity
from utils.mailer import send_order_status_email
from werkzeug.security import generate_password_hash
from functools import wraps
from datetime import datetime

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

@admin.route('/orders')
@permission_required('manage_orders')
def manage_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/manage_orders.html', orders=orders)

@admin.route('/users')
@permission_required('manage_users')
def manage_users():
    users = User.query.all()
    roles = User.ROLES
    return render_template('admin/users.html', users=users, roles=roles)

@admin.route('/users/add', methods=['GET', 'POST'])
@permission_required('manage_users')
def add_user():
    form = UserForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data
        )
        if form.password.data:
            user.password_hash = generate_password_hash(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('User added successfully!', 'success')
        return redirect(url_for('admin.manage_users'))
    return render_template('admin/user_form.html', form=form)

@admin.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@permission_required('manage_users')
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        if form.password.data:
            user.password_hash = generate_password_hash(form.password.data)
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin.manage_users'))
    return render_template('admin/user_form.html', form=form, user=user)

@admin.route('/users/delete/<int:user_id>', methods=['POST'])
@permission_required('manage_users')
def delete_user(user_id):
    if current_user.id == user_id:
        return jsonify({'success': False, 'error': 'Cannot delete your own account'})
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})

@admin.route('/users/<int:user_id>/activity')
@permission_required('manage_users')
def user_activity(user_id):
    user = User.query.get_or_404(user_id)
    activities = UserActivity.query.filter_by(user_id=user_id).order_by(UserActivity.timestamp.desc()).all()
    return render_template('admin/user_activities.html', user=user, activities=activities)

@admin.route('/categories')
@permission_required('manage_categories')
def manage_categories():
    categories = Category.query.order_by(Category.display_order).all()
    form = CategoryForm()
    return render_template('admin/categories.html', categories=categories, form=form)

@admin.route('/categories/add', methods=['GET', 'POST'])
@permission_required('manage_categories')
def add_category():
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            description=form.description.data,
            display_order=form.display_order.data
        )
        db.session.add(category)
        db.session.commit()
        flash('Category added successfully!', 'success')
        return redirect(url_for('admin.manage_categories'))
    return render_template('admin/category_form.html', form=form)

@admin.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@permission_required('manage_categories')
def edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=category)
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        category.display_order = form.display_order.data
        db.session.commit()
        flash('Category updated successfully!', 'success')
        return redirect(url_for('admin.manage_categories'))
    return render_template('admin/category_form.html', form=form, category=category)

@admin.route('/categories/delete/<int:category_id>', methods=['POST'])
@permission_required('manage_categories')
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    if category.books:
        return jsonify({'success': False, 'error': 'Cannot delete category with books'})
    db.session.delete(category)
    db.session.commit()
    return jsonify({'success': True})

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