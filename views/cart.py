from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import CartItem, Book, Order, OrderItem
from extensions import db
from utils.activity_logger import log_user_activity
from sqlalchemy import func

cart = Blueprint('cart', __name__)

@cart.route('/cart')
@login_required
def view_cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.total for item in cart_items)
    return render_template('cart/view.html', cart_items=cart_items, total=total)

@cart.route('/cart/count')
@login_required
def get_cart_count():
    try:
        count = CartItem.query.filter_by(user_id=current_user.id).with_entities(func.sum(CartItem.quantity)).scalar() or 0
        return jsonify({'success': True, 'count': int(count)})
    except Exception as e:
        db.session.rollback()  # Add rollback on error
        return jsonify({'success': False, 'error': str(e)})

@cart.route('/cart/add/<int:book_id>', methods=['POST'])
@login_required
def add_to_cart(book_id):
    try:
        book = Book.query.get_or_404(book_id)
        if book.stock <= 0:
            return jsonify({'success': False, 'error': 'Book out of stock'})
        
        cart_item = CartItem.query.filter_by(user_id=current_user.id, book_id=book_id).first()
        if cart_item:
            if cart_item.quantity >= book.stock:
                return jsonify({'success': False, 'error': 'Not enough stock available'})
            cart_item.quantity += 1
        else:
            cart_item = CartItem(user_id=current_user.id, book_id=book_id, quantity=1)
            db.session.add(cart_item)
        
        db.session.commit()
        log_user_activity(current_user, 'cart_add', f'Added {book.title} to cart')
        
        return jsonify({'success': True, 'message': 'Book added to cart successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@cart.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    try:
        quantity = request.json.get('quantity', 0)
        cart_item = CartItem.query.get_or_404(item_id)
        
        if cart_item.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Unauthorized'})
        
        if quantity <= 0:
            db.session.delete(cart_item)
        else:
            cart_item.quantity = quantity
        
        db.session.commit()
        log_user_activity(current_user, 'cart_update', f'Updated cart item quantity to {quantity}')
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@cart.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    try:
        cart_item = CartItem.query.get_or_404(item_id)
        if cart_item.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Unauthorized'})
        
        db.session.delete(cart_item)
        db.session.commit()
        
        log_user_activity(current_user, 'cart_remove', f'Removed {cart_item.book.title} from cart')
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})
