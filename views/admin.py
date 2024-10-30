from flask import Blueprint, render_template, redirect, url_for, flash, request
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
    return render_template('admin/dashboard.html', books=books, orders=orders)

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
            stock=form.stock.data
        )
        db.session.add(book)
        db.session.commit()
        flash('Book added successfully.')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/book_form.html', form=form, title='Add Book')

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
