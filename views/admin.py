from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import User, Book, Order, Category, Review, UserActivity, BookFormat, BookSeries
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

@admin.route('/books/add', methods=['GET', 'POST'])
@permission_required('manage_books')
def add_book():
    form = BookForm()
    if form.validate_on_submit():
        try:
            # Validate required fields
            if not form.title.data or not form.author.data or not form.price.data:
                flash('Please fill in all required fields.', 'danger')
                return render_template('admin/book_form.html', form=form)

            # Validate price
            if form.price.data <= 0:
                flash('Price must be greater than zero.', 'danger')
                return render_template('admin/book_form.html', form=form)

            # Create new book
            book = Book(
                title=form.title.data,
                author=form.author.data,
                price=form.price.data,
                description=form.description.data,
                image_url=form.image_url.data,
                stock=form.stock.data,
                category=form.category_id.data,
                is_featured=form.is_featured.data,
                isbn=form.isbn.data,
                publisher=form.publisher.data,
                publication_date=form.publication_date.data,
                page_count=form.page_count.data,
                language=form.language.data,
                tags=form.tags.data
            )

            # Validate and handle series information
            if form.series_id.data:
                series = BookSeries.query.get(form.series_id.data)
                if not series:
                    flash('Selected series does not exist.', 'danger')
                    return render_template('admin/book_form.html', form=form)
                book.series_id = series.id
                book.series_order = form.series_order.data

            # Validate and add book formats
            if form.formats.data:
                for format_data in form.formats.data:
                    if not format_data.get('format_type') or not format_data.get('price'):
                        flash('All book format fields are required.', 'danger')
                        return render_template('admin/book_form.html', form=form)
                    
                    if float(format_data['price']) <= 0:
                        flash('Format prices must be greater than zero.', 'danger')
                        return render_template('admin/book_form.html', form=form)

                    format = BookFormat(
                        format_type=format_data['format_type'],
                        price=float(format_data['price']),
                        stock=int(format_data.get('stock', 0)),
                        isbn=format_data.get('isbn')
                    )
                    book.formats.append(format)

            db.session.add(book)
            db.session.commit()
            flash('Book added successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding book: {str(e)}', 'danger')
            return render_template('admin/book_form.html', form=form)
    
    # If form validation fails, show errors
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
    
    return render_template('admin/book_form.html', form=form)

@admin.route('/delete_book/<int:book_id>', methods=['POST'])
@permission_required('manage_books')
def delete_book(book_id):
    try:
        book = Book.query.get_or_404(book_id)
        
        # Delete associated formats
        for format in book.formats:
            db.session.delete(format)
        
        # Delete the book
        db.session.delete(book)
        db.session.commit()
        
        log_user_activity(current_user, 'book_deleted', f'Deleted book: {book.title}')
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
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
            book.is_featured = form.is_featured.data
            book.isbn = form.isbn.data
            book.publisher = form.publisher.data
            book.publication_date = form.publication_date.data
            book.page_count = form.page_count.data
            book.language = form.language.data
            book.tags = form.tags.data
            
            # Update series information
            book.series_id = form.series_id.data
            book.series_order = form.series_order.data if form.series_id.data else None
            
            # Update formats
            book.formats = []
            for format_data in form.formats.data:
                if not format_data.get('format_type') or not format_data.get('price'):
                    continue
                format = BookFormat(
                    format_type=format_data['format_type'],
                    price=format_data['price'],
                    stock=format_data.get('stock', 0),
                    isbn=format_data.get('isbn')
                )
                book.formats.append(format)
            
            db.session.commit()
            flash('Book updated successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating book: {str(e)}', 'danger')
        
    return render_template('admin/book_form.html', form=form, book=book)

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
    try:
        category = Category.query.get_or_404(category_id)
        if category.books:
            return jsonify({'success': False, 'error': 'Cannot delete category with books'})
        db.session.delete(category)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

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

@admin.route('/series')
@permission_required('manage_books')
def manage_series():
    series_list = BookSeries.query.order_by(BookSeries.title).all()
    return render_template('admin/manage_series.html', series_list=series_list)

@admin.route('/series/add', methods=['POST'])
@permission_required('manage_books')
def add_series():
    try:
        data = request.get_json()
        series = BookSeries(
            title=data['title'],
            total_books=int(data['total_books'])
        )
        db.session.add(series)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/series/edit/<int:series_id>', methods=['POST'])
@permission_required('manage_books')
def edit_series(series_id):
    try:
        data = request.get_json()
        series = BookSeries.query.get_or_404(series_id)
        series.title = data['title']
        series.total_books = int(data['total_books'])
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/series/delete/<int:series_id>', methods=['POST'])
@permission_required('manage_books')
def delete_series(series_id):
    try:
        series = BookSeries.query.get_or_404(series_id)
        if series.books:
            return jsonify({
                'success': False, 
                'error': 'Cannot delete series with associated books'
            })
        db.session.delete(series)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})