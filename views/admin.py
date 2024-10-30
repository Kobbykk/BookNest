from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import Book, Order, OrderItem
from forms import BookForm
from app import db
from utils.email import send_order_status_email

admin = Blueprint('admin', __name__)

@admin.route('/admin')
@login_required
def dashboard():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))
    books = Book.query.all()
    orders = Order.query.all()
    
    # Get unique categories
    categories = db.session.query(Book.category).distinct().all()
    categories = [cat[0] for cat in categories]
    
    return render_template('admin/dashboard.html', 
                         books=books, 
                         orders=orders, 
                         categories=categories)

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
            category=form.category.data
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
        book.category = form.category.data
        
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
    category = request.json.get('category')
    value = request.json.get('value')
    
    if not all([action, category, value]):
        return jsonify({'success': False, 'error': 'Missing required fields'})
    
    try:
        books = Book.query.filter_by(category=category).all()
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
