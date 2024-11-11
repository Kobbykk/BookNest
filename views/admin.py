from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import User, Book, Order, Review, UserActivity, BookFormat, Category
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
    try:
        books = Book.query.all()
        orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
        categories = Category.query.order_by(Category.display_order).all()
        return render_template('admin/dashboard.html', 
                            books=books,
                            orders=orders,
                            categories=categories)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        return redirect(url_for('main.index'))

@admin.route('/categories', methods=['GET', 'POST'])
@permission_required('manage_categories')
def manage_categories():
    form = CategoryForm()
    if form.validate_on_submit():
        try:
            # Check if category exists
            category = Category.query.filter_by(name=form.name.data).first()
            
            if category and not form.old_category.data:
                flash('Category already exists.', 'danger')
                return redirect(url_for('admin.manage_categories'))
                
            if not category:
                # Create new category
                category = Category(
                    name=form.name.data,
                    description=form.description.data,
                    display_order=form.display_order.data
                )
                db.session.add(category)
                db.session.flush()  # Get category ID
                
            else:
                # Update existing category
                category.description = form.description.data
                category.display_order = form.display_order.data
            
            # Handle category rename
            if form.old_category.data and form.old_category.data != form.name.data:
                # Update all books with old category name
                Book.query.filter_by(category_name=form.old_category.data).update({
                    'category_id': category.id,
                    'category_name': form.name.data
                })
            
            db.session.commit()
            flash('Category saved successfully!', 'success')
            return redirect(url_for('admin.manage_categories'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving category: {str(e)}', 'danger')
    
    categories = Category.query.order_by(Category.display_order).all()
    return render_template('admin/categories.html', categories=categories, form=form)

@admin.route('/categories/delete/<int:category_id>', methods=['POST'])
@permission_required('manage_categories')
def delete_category(category_id):
    try:
        category = Category.query.get_or_404(category_id)
        
        # Update books to remove category reference
        Book.query.filter_by(category_id=category_id).update({
            'category_id': None,
            'category_name': None
        })
        
        db.session.delete(category)
        db.session.commit()
        
        flash('Category deleted successfully!', 'success')
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/books/add', methods=['GET', 'POST'])
@permission_required('manage_books')
def add_book():
    form = BookForm()
    if form.validate_on_submit():
        try:
            book = Book()
            
            # Get or create category
            category = Category.query.filter_by(name=form.category.data).first()
            if not category:
                category = Category(
                    name=form.category.data,
                    description=f"Books about {form.category.data.lower()}",
                    display_order=99
                )
                db.session.add(category)
                db.session.flush()
            
            # Populate book attributes
            book_data = {
                'title': form.title.data,
                'author': form.author.data,
                'price': form.price.data,
                'description': form.description.data,
                'image_url': form.image_url.data,
                'stock': form.stock.data,
                'category_id': category.id,
                'category_name': category.name,
                'is_featured': form.is_featured.data
            }
            
            for key, value in book_data.items():
                setattr(book, key, value)
            
            # Add book formats
            for format_form in form.formats:
                book_format = BookFormat(
                    format_type=format_form.format_type.data,
                    price=format_form.price.data,
                    stock=format_form.stock.data,
                    isbn=format_form.isbn.data
                )
                book.formats.append(book_format)
            
            db.session.add(book)
            db.session.commit()
            
            flash('Book added successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding book: {str(e)}', 'danger')
    
    return render_template('admin/book_form.html', form=form)

@admin.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
@permission_required('manage_books')
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    form = BookForm(obj=book)
    
    if form.validate_on_submit():
        try:
            # Get or create category
            category = Category.query.filter_by(name=form.category.data).first()
            if not category:
                category = Category(
                    name=form.category.data,
                    description=f"Books about {form.category.data.lower()}",
                    display_order=99
                )
                db.session.add(category)
                db.session.flush()
            
            # Update book attributes
            book_data = {
                'title': form.title.data,
                'author': form.author.data,
                'price': form.price.data,
                'description': form.description.data,
                'image_url': form.image_url.data,
                'stock': form.stock.data,
                'category_id': category.id,
                'category_name': category.name,
                'is_featured': form.is_featured.data
            }
            
            for key, value in book_data.items():
                setattr(book, key, value)
            
            # Update book formats
            book.formats = []
            for format_form in form.formats:
                book_format = BookFormat(
                    format_type=format_form.format_type.data,
                    price=format_form.price.data,
                    stock=format_form.stock.data,
                    isbn=format_form.isbn.data
                )
                book.formats.append(book_format)
            
            db.session.commit()
            flash('Book updated successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating book: {str(e)}', 'danger')
    
    return render_template('admin/book_form.html', form=form, book=book)

@admin.route('/books/delete/<int:book_id>', methods=['POST'])
@permission_required('manage_books')
def delete_book(book_id):
    try:
        book = Book.query.get_or_404(book_id)
        db.session.delete(book)
        db.session.commit()
        flash('Book deleted successfully!', 'success')
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
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/bulk_update_books', methods=['POST'])
@permission_required('manage_books')
def bulk_update_books():
    try:
        data = request.get_json()
        books = Book.query.filter_by(category_name=data['category']).all()
        
        for book in books:
            if data['action'] == 'price_adjust':
                book.price = book.price * (1 + float(data['value']) / 100)
            elif data['action'] == 'stock_adjust':
                book.stock = max(0, book.stock + int(data['value']))
        
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
        
        # Send email notification
        send_order_status_email(order.user.email, order.id, order.status, order.items)
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})
