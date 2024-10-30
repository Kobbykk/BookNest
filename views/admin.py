from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import Book, Order, OrderItem, User, Category, Discount, BookDiscount
from forms import BookForm, CategoryForm, DiscountForm
from app import db
from utils.email import send_order_status_email
from datetime import datetime

admin = Blueprint('admin', __name__)

@admin.route('/admin')
@login_required
def dashboard():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))
    books = Book.query.all()
    orders = Order.query.all()
    users = User.query.all()
    categories = Category.query.all()
    discounts = Discount.query.all()
    
    return render_template('admin/dashboard.html', 
                         books=books, 
                         orders=orders,
                         users=users,
                         categories=categories,
                         discounts=discounts)

@admin.route('/admin/users')
@login_required
def manage_users():
    if not current_user.is_admin:
        return redirect(url_for('main.index'))
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin.route('/admin/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
def toggle_admin(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'})
    
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'success': False, 'error': 'Cannot modify your own admin status'})
    
    user.is_admin = not user.is_admin
    db.session.commit()
    return jsonify({'success': True, 'is_admin': user.is_admin})

@admin.route('/admin/categories', methods=['GET', 'POST'])
@login_required
def manage_categories():
    if not current_user.is_admin:
        return redirect(url_for('main.index'))
    
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(category)
        db.session.commit()
        flash('Category added successfully.')
        return redirect(url_for('admin.manage_categories'))
    
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories, form=form)

@admin.route('/admin/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    if not current_user.is_admin:
        return redirect(url_for('main.index'))
    
    category = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=category)
    
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        db.session.commit()
        flash('Category updated successfully.')
        return redirect(url_for('admin.manage_categories'))
    
    return render_template('admin/category_form.html', form=form, category=category)

@admin.route('/admin/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'})
    
    category = Category.query.get_or_404(category_id)
    if category.books:
        return jsonify({'success': False, 'error': 'Cannot delete category with books'})
    
    try:
        db.session.delete(category)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/admin/discounts', methods=['GET', 'POST'])
@login_required
def manage_discounts():
    if not current_user.is_admin:
        return redirect(url_for('main.index'))
    
    form = DiscountForm()
    if form.validate_on_submit():
        discount = Discount(
            name=form.name.data,
            description=form.description.data,
            percentage=form.percentage.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            active=form.active.data
        )
        db.session.add(discount)
        db.session.flush()
        
        # Apply discount to all books in the selected category
        category_id = form.books.data
        books = Book.query.filter_by(category_id=category_id).all()
        for book in books:
            book_discount = BookDiscount(
                book_id=book.id,
                discount_id=discount.id,
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                active=form.active.data
            )
            db.session.add(book_discount)
        
        db.session.commit()
        flash('Discount added successfully.')
        return redirect(url_for('admin.manage_discounts'))
    
    discounts = Discount.query.all()
    return render_template('admin/discounts.html', discounts=discounts, form=form)

# Existing routes...
@admin.route('/admin/book/add', methods=['GET', 'POST'])
@login_required
def add_book():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))
    
    form = BookForm()
    if form.validate_on_submit():
        book = Book(
            title=form.title.data,
            author=form.author.data,
            price=form.price.data,
            description=form.description.data,
            image_url=form.image_url.data,
            stock=form.stock.data,
            category_id=form.category_id.data
        )
        db.session.add(book)
        db.session.commit()
        flash('Book added successfully.')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/book_form.html', form=form, title='Add Book')

@admin.route('/admin/book/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))
    
    book = Book.query.get_or_404(book_id)
    form = BookForm(obj=book)
    
    if form.validate_on_submit():
        book.title = form.title.data
        book.author = form.author.data
        book.price = form.price.data
        book.description = form.description.data
        book.image_url = form.image_url.data
        book.stock = form.stock.data
        book.category_id = form.category_id.data
        
        db.session.commit()
        flash('Book updated successfully.')
        return redirect(url_for('admin.dashboard'))
    
    return render_template('admin/book_form.html', form=form, title='Edit Book')

@admin.route('/admin/book/<int:book_id>/delete', methods=['POST'])
@login_required
def delete_book(book_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'})
    
    book = Book.query.get_or_404(book_id)
    try:
        db.session.delete(book)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/admin/book/update-stock', methods=['POST'])
@login_required
def update_stock():
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'})
    
    book_id = request.json.get('book_id')
    new_stock = request.json.get('stock')
    
    if not book_id or new_stock is None:
        return jsonify({'success': False, 'error': 'Missing required fields'})
    
    book = Book.query.get_or_404(book_id)
    try:
        book.stock = new_stock
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/admin/books/bulk-update', methods=['POST'])
@login_required
def bulk_update_books():
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'})
    
    action = request.json.get('action')
    category_id = request.json.get('category')
    value = request.json.get('value')
    
    if not all([action, category_id, value]):
        return jsonify({'success': False, 'error': 'Missing required fields'})
    
    try:
        books = Book.query.filter_by(category_id=category_id).all()
        if action == 'price_adjust':
            for book in books:
                # Value is percentage change
                adjustment = book.price * (float(value) / 100)
                book.price = max(0, book.price + adjustment)
        elif action == 'stock_adjust':
            for book in books:
                # Value is absolute change
                book.stock = max(0, book.stock + int(value))
                
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/admin/order/<int:order_id>/update-status', methods=['POST'])
@login_required
def update_order_status(order_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))
        
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    if new_status in ['pending', 'shipped', 'completed']:
        order.status = new_status
        db.session.commit()
        
        # Send email notification
        send_order_status_email(
            user_email=order.user.email,
            order_id=order.id,
            status=new_status,
            items=order.items
        )
        
        flash(f'Order status updated to {new_status}.')
    return redirect(url_for('admin.dashboard'))
