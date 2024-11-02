from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import CartItem, Book, Order, OrderItem, db
from utils.activity_logger import log_user_activity
from sqlalchemy import func
import stripe
from datetime import datetime

cart = Blueprint('cart', __name__)

@cart.route('/cart/count')
def get_cart_count():
    """Get the current cart count. Returns 0 for unauthenticated users."""
    try:
        if not current_user.is_authenticated:
            return jsonify({'success': True, 'count': 0})
            
        count = db.session.query(
            func.coalesce(func.sum(CartItem.quantity), 0)
        ).filter_by(user_id=current_user.id).scalar() or 0
        
        return jsonify({'success': True, 'count': int(count)})
    except Exception as e:
        current_app.logger.error(f"Error getting cart count: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to fetch cart count'}), 500

@cart.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    """Add an item to cart. Requires authentication."""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Invalid request format'}), 400
        
        data = request.get_json()
        book_id = data.get('book_id')
        quantity = int(data.get('quantity', 1))

        if not book_id or quantity < 1:
            return jsonify({'success': False, 'error': 'Invalid request parameters'}), 400

        book = Book.query.get(book_id)
        if not book:
            return jsonify({'success': False, 'error': 'Book not found'}), 404

        if quantity > book.stock:
            return jsonify({'success': False, 'error': 'Not enough stock available'}), 400

        cart_item = CartItem.query.filter_by(
            user_id=current_user.id,
            book_id=book_id
        ).first()

        if cart_item:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > book.stock:
                return jsonify({'success': False, 'error': 'Not enough stock available'}), 400
            cart_item.quantity = new_quantity
        else:
            cart_item = CartItem(
                user_id=current_user.id,
                book_id=book_id,
                quantity=quantity
            )
            db.session.add(cart_item)

        db.session.commit()
        log_user_activity(current_user, 'cart_add', f'Added book #{book_id} to cart')
        
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Error adding to cart: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to add item to cart'}), 500

@cart.route('/cart')
@login_required
def view_cart():
    """View cart contents. Requires authentication."""
    try:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        total = sum(item.total for item in cart_items)
        return render_template('cart/cart.html', cart_items=cart_items, total=total)
    except Exception as e:
        current_app.logger.error(f"Error viewing cart: {str(e)}")
        flash('An error occurred while loading your cart.', 'danger')
        return redirect(url_for('main.index'))

@cart.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart_quantity(item_id):
    """Update cart item quantity. Requires authentication."""
    try:
        data = request.get_json()
        quantity = int(data.get('quantity', 0))

        if quantity < 0:
            return jsonify({'success': False, 'error': 'Invalid quantity'}), 400

        cart_item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first()
        if not cart_item:
            return jsonify({'success': False, 'error': 'Item not found'}), 404

        if quantity == 0:
            db.session.delete(cart_item)
        else:
            if quantity > cart_item.book.stock:
                return jsonify({'success': False, 'error': 'Not enough stock available'}), 400
            cart_item.quantity = quantity

        db.session.commit()
        log_user_activity(current_user, 'cart_update', f'Updated quantity for book #{cart_item.book_id}')
        
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Error updating cart: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to update cart'}), 500

@cart.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    """Remove item from cart. Requires authentication."""
    try:
        cart_item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first()
        if not cart_item:
            return jsonify({'success': False, 'error': 'Item not found'}), 404

        db.session.delete(cart_item)
        db.session.commit()
        log_user_activity(current_user, 'cart_remove', f'Removed book #{cart_item.book_id} from cart')
        
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Error removing from cart: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to remove item from cart'}), 500
