from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import Book, Order, OrderItem, User, Category, Discount, BookDiscount, UserActivity, Review
from forms import BookForm, CategoryForm, DiscountForm
from app import db
from utils.email import send_order_status_email
from datetime import datetime, timedelta
from sqlalchemy import desc, or_
from werkzeug.utils import secure_filename
from utils.activity_logger import log_user_activity

admin = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Access denied.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin.route('/dashboard')
@admin_required
def dashboard():
    books = Book.query.all()
    orders = Order.query.order_by(Order.created_at.desc()).all()
    users = User.query.all()
    categories = Category.query.all()
    discounts = Discount.query.all()
    
    return render_template('admin/dashboard.html', 
                         books=books,
                         orders=orders,
                         users=users,
                         categories=categories,
                         discounts=discounts)

@admin.route('/manage_orders')
@admin_required
def manage_orders():
    # Get filter parameters
    status = request.args.get('status', '')
    search = request.args.get('search', '')
    
    # Build query
    query = Order.query
    
    if status:
        query = query.filter(Order.status == status)
    
    if search:
        query = query.join(User).filter(
            or_(
                Order.id.cast(db.String).ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )
    
    # Get orders with filters applied
    orders = query.order_by(Order.created_at.desc()).all()
    
    return render_template('admin/manage_orders.html', orders=orders)

@admin.route('/order_details/<int:order_id>')
@admin_required
def order_details(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        
        return jsonify({
            'success': True,
            'order': {
                'id': order.id,
                'user_email': order.user.email,
                'created_at': order.created_at.isoformat(),
                'status': order.status,
                'total': float(order.total)
            },
            'items': [{
                'book_title': item.book.title,
                'quantity': item.quantity,
                'price': float(item.price)
            } for item in order.items]
        })
    except Exception as e:
        current_app.logger.error(f'Error fetching order details: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/update_order_status/<int:order_id>', methods=['POST'])
@admin_required
def update_order_status(order_id):
    data = request.get_json()
    new_status = data.get('status')
    
    if not new_status:
        return jsonify({'success': False, 'error': 'Status is required'})
    
    try:
        order = Order.query.get_or_404(order_id)
        order.status = new_status
        db.session.commit()
        
        try:
            send_order_status_email(order.user.email, order.id, new_status, order.items)
        except Exception as e:
            current_app.logger.error(f'Error sending status update email: {str(e)}')
        
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f'Error updating order status: {str(e)}')
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/add_book', methods=['GET', 'POST'])
@admin_required
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
            flash('Book added successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            current_app.logger.error(f'Error adding book: {str(e)}')
            flash('Error adding book.', 'danger')
            db.session.rollback()
    
    return render_template('admin/book_form.html', form=form)

@admin.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
@admin_required
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
            flash('Book updated successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            current_app.logger.error(f'Error updating book: {str(e)}')
            flash('Error updating book.', 'danger')
            db.session.rollback()
    
    return render_template('admin/book_form.html', form=form, book=book)

@admin.route('/delete_book/<int:book_id>', methods=['POST'])
@admin_required
def delete_book(book_id):
    try:
        book = Book.query.get_or_404(book_id)
        db.session.delete(book)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f'Error deleting book: {str(e)}')
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/update_book_stock', methods=['POST'])
@admin_required
def update_book_stock():
    data = request.get_json()
    book_id = data.get('book_id')
    new_stock = data.get('stock')
    
    if not book_id or new_stock is None:
        return jsonify({'success': False, 'error': 'Missing required data'})
    
    try:
        book = Book.query.get_or_404(book_id)
        book.stock = max(0, int(new_stock))
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f'Error updating stock: {str(e)}')
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/bulk_update_books', methods=['POST'])
@admin_required
def bulk_update_books():
    data = request.get_json()
    action = data.get('action')
    category = data.get('category')
    value = data.get('value')
    
    if not all([action, category, value]):
        return jsonify({'success': False, 'error': 'Missing required data'})
    
    try:
        books = Book.query.filter_by(category=category).all()
        for book in books:
            if action == 'price_adjust':
                adjustment = float(value) / 100
                book.price = round(book.price * (1 + adjustment), 2)
            elif action == 'stock_adjust':
                book.stock = max(0, book.stock + int(value))
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f'Error in bulk update: {str(e)}')
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/manage_users')
@admin_required
def manage_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    try:
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            return jsonify({'success': False, 'error': 'Cannot modify your own admin status'})
            
        user.is_admin = not user.is_admin
        log_user_activity(current_user, 'admin_toggle', 
                         f'{"Granted" if user.is_admin else "Revoked"} admin privileges for {user.email}')
        db.session.commit()
        return jsonify({'success': True, 'is_admin': user.is_admin})
    except Exception as e:
        current_app.logger.error(f'Error toggling admin status: {str(e)}')
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/manage_categories', methods=['GET', 'POST'])
@admin_required
def manage_categories():
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
            flash('Category added successfully.', 'success')
        except Exception as e:
            current_app.logger.error(f'Error adding category: {str(e)}')
            flash('Error adding category.', 'danger')
            db.session.rollback()
    
    categories = Category.query.order_by(Category.display_order).all()
    return render_template('admin/categories.html', categories=categories, form=form)
