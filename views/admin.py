from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import User, Book, Order, Category, Review, UserActivity
from forms import UserForm, CategoryForm, BookForm
from app import db
from utils.activity_logger import log_user_activity
from utils.email import send_order_status_email
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

@admin.route('/manage_users')
@permission_required('manage_users')
def manage_users():
    # Get role filter from query parameters
    role_filter = request.args.get('role', '')
    search_query = request.args.get('search', '')
    
    # Build the query
    query = User.query
    if role_filter:
        query = query.filter_by(role=role_filter)
    if search_query:
        query = query.filter(
            (User.username.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%'))
        )
    
    users = query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users, roles=User.ROLES)

@admin.route('/add_user', methods=['GET', 'POST'])
@permission_required('manage_users')
def add_user():
    form = UserForm()
    if form.validate_on_submit():
        try:
            # Check if email already exists
            if User.query.filter(User.email.ilike(form.email.data)).first():
                flash('Email already registered.', 'danger')
                return render_template('admin/user_form.html', form=form)
            
            user = User(
                username=form.username.data,
                email=form.email.data.lower(),
                password_hash=generate_password_hash(form.password.data),
                role=form.role.data,
                is_admin=form.role.data == 'admin'
            )
            db.session.add(user)
            db.session.commit()
            
            log_user_activity(current_user, 'user_create', 
                            f'Created new user {user.email} with role {user.role}')
            
            flash('User added successfully!', 'success')
            return redirect(url_for('admin.manage_users'))
        except Exception as e:
            current_app.logger.error(f'Error adding user: {str(e)}')
            flash('Error adding user.', 'danger')
            db.session.rollback()
    
    return render_template('admin/user_form.html', form=form)

@admin.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@permission_required('manage_users')
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    
    if form.validate_on_submit():
        try:
            # Check if email is being changed and already exists
            if user.email != form.email.data and \
               User.query.filter(User.email.ilike(form.email.data)).first():
                flash('Email already registered.', 'danger')
                return render_template('admin/user_form.html', form=form, user=user)
            
            # Prevent changing own role from admin
            if user.id == current_user.id and user.role == 'admin' and form.role.data != 'admin':
                flash('You cannot remove your own admin role.', 'danger')
                return render_template('admin/user_form.html', form=form, user=user)
            
            user.username = form.username.data
            user.email = form.email.data.lower()
            if form.password.data:
                user.password_hash = generate_password_hash(form.password.data)
            user.role = form.role.data
            user.is_admin = form.role.data == 'admin'
            
            db.session.commit()
            
            log_user_activity(current_user, 'user_update', 
                            f'Updated user {user.email} role to {user.role}')
            
            flash('User updated successfully!', 'success')
            return redirect(url_for('admin.manage_users'))
        except Exception as e:
            current_app.logger.error(f'Error updating user: {str(e)}')
            flash('Error updating user.', 'danger')
            db.session.rollback()
    
    return render_template('admin/user_form.html', form=form, user=user)

@admin.route('/delete_user/<int:user_id>', methods=['POST'])
@permission_required('manage_users')
def delete_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            return jsonify({'success': False, 'error': 'Cannot delete your own account'})
        
        if user.role == 'admin':
            admin_count = User.query.filter_by(role='admin').count()
            if admin_count <= 1:
                return jsonify({'success': False, 'error': 'Cannot delete the last admin user'})
        
        db.session.delete(user)
        db.session.commit()
        
        log_user_activity(current_user, 'user_delete', f'Deleted user {user.email}')
        
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f'Error deleting user: {str(e)}')
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/user_activity/<int:user_id>')
@permission_required('manage_users')
def user_activity(user_id):
    user = User.query.get_or_404(user_id)
    activities = UserActivity.query.filter_by(user_id=user_id)\
                          .order_by(UserActivity.timestamp.desc())\
                          .limit(50).all()
    return render_template('admin/user_activities.html', user=user, activities=activities)

@admin.route('/manage_categories')
@permission_required('manage_categories')
def manage_categories():
    categories = Category.query.order_by(Category.display_order).all()
    form = CategoryForm()
    return render_template('admin/categories.html', categories=categories, form=form)

@admin.route('/add_category', methods=['POST'])
@permission_required('manage_categories')
def add_category():
    form = CategoryForm()
    if form.validate_on_submit():
        try:
            category = Category(
                name=form.name.data,
                description=form.description.data,
                display_order=form.display_order.data
            )
            db.session.add(category)
            db.session.commit()
            flash('Category added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error adding category.', 'danger')
    return redirect(url_for('admin.manage_categories'))

@admin.route('/add_book', methods=['GET', 'POST'])
@permission_required('manage_books')
def add_book():
    form = BookForm()
    if form.validate_on_submit():
        try:
            book = Book(
                title=form.title.data,
                author=form.author.data,
                price=form.price.data,
                description=form.description.data,
                image_url=form.image_url.data,
                stock=form.stock.data,
                category=form.category_id.data
            )
            db.session.add(book)
            db.session.commit()
            
            log_user_activity(current_user, 'book_create', f'Added new book: {book.title}')
            flash('Book added successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding book.', 'danger')
    return render_template('admin/book_form.html', form=form)

@admin.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
@permission_required('manage_books')
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    form = BookForm(obj=book)
    
    if form.validate_on_submit():
        try:
            book.title = form.title.data
            book.author = form.author.data
            book.price = form.price.data
            book.description = form.description.data
            book.image_url = form.image_url.data
            book.stock = form.stock.data
            book.category = form.category_id.data
            
            db.session.commit()
            log_user_activity(current_user, 'book_update', f'Updated book: {book.title}')
            flash('Book updated successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating book.', 'danger')
    
    return render_template('admin/book_form.html', form=form, book=book)

@admin.route('/delete_book/<int:book_id>', methods=['POST'])
@permission_required('manage_books')
def delete_book(book_id):
    try:
        book = Book.query.get_or_404(book_id)
        db.session.delete(book)
        db.session.commit()
        
        log_user_activity(current_user, 'book_delete', f'Deleted book: {book.title}')
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/update_book_stock', methods=['POST'])
@permission_required('manage_books')
def update_book_stock():
    try:
        data = request.get_json()
        book = Book.query.get_or_404(data['book_id'])
        book.stock = data['stock']
        db.session.commit()
        
        log_user_activity(current_user, 'stock_update', 
                         f'Updated stock for {book.title} to {book.stock}')
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/bulk_update_books', methods=['POST'])
@permission_required('manage_books')
def bulk_update_books():
    try:
        data = request.get_json()
        action = data.get('action')
        category = data.get('category')
        value = float(data.get('value', 0))
        
        query = Book.query
        if category:
            query = query.filter_by(category=category)
        
        books = query.all()
        for book in books:
            if action == 'price_adjust':
                book.price = book.price * (1 + value/100)
            elif action == 'stock_adjust':
                book.stock = max(0, book.stock + int(value))
        
        db.session.commit()
        log_user_activity(current_user, 'bulk_update', 
                         f'Bulk updated {len(books)} books: {action} by {value}')
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/manage_orders')
@permission_required('manage_orders')
def manage_orders():
    # Get filter parameters
    status_filter = request.args.get('status', '')
    search_query = request.args.get('search', '')
    
    # Build the query
    query = Order.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if search_query:
        query = query.join(User).filter(
            (Order.id.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%'))
        )
    
    orders = query.order_by(Order.created_at.desc()).all()
    return render_template('admin/manage_orders.html', orders=orders)

@admin.route('/order_details/<int:order_id>')
@permission_required('manage_orders')
def order_details(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_details.html', order=order)

@admin.route('/update_order_status/<int:order_id>', methods=['POST'])
@permission_required('manage_orders')
def update_order_status(order_id):
    try:
        data = request.get_json()
        order = Order.query.get_or_404(order_id)
        order.status = data['status']
        db.session.commit()
        
        # Send email notification
        send_order_status_email(order.user.email, order.id, order.status, order.items)
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})
