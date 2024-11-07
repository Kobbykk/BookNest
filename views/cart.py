from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import CartItem, Book, Order, OrderItem, db
from utils.activity_logger import log_user_activity
from sqlalchemy import func
import stripe
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
cart = Blueprint('cart', __name__, url_prefix='/cart')

@cart.route('/')
@login_required
def view_cart():
    try:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        total = sum(item.total for item in cart_items)
        return render_template('cart/cart.html', cart_items=cart_items, total=total)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error viewing cart: {str(e)}")
        flash('An error occurred while loading your cart.', 'danger')
        return redirect(url_for('main.index'))

@cart.route('/checkout')
@login_required
def checkout():
    try:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            flash('Your cart is empty.', 'warning')
            return redirect(url_for('main.index'))
            
        total = sum(item.total for item in cart_items)
        return render_template('cart/checkout.html', 
                             cart_items=cart_items,
                             total=total,
                             stripe_publishable_key=current_app.config['STRIPE_PUBLISHABLE_KEY'])
    except Exception as e:
        logger.error(f"Error in checkout: {str(e)}")
        flash('An error occurred while processing your request.', 'danger')
        return redirect(url_for('main.index'))

@cart.route('/count')
def get_cart_count():
    try:
        if not current_user.is_authenticated:
            return jsonify({'success': True, 'count': 0})
            
        count = CartItem.query.filter_by(user_id=current_user.id).with_entities(func.sum(CartItem.quantity)).scalar() or 0
        return jsonify({'success': True, 'count': int(count)})
    except Exception as e:
        logger.error(f"Error in get_cart_count: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@cart.route('/add', methods=['POST'])
@login_required
def add_to_cart():
    try:
        data = request.get_json()
        if not data or 'book_id' not in data:
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400
            
        book_id = data['book_id']
        book = Book.query.get_or_404(book_id)
        
        if not book.stock:
            return jsonify({'success': False, 'error': 'Book is out of stock'}), 400

        cart_item = CartItem.query.filter_by(user_id=current_user.id, book_id=book_id).first()
        
        if cart_item:
            if cart_item.quantity >= book.stock:
                return jsonify({'success': False, 'error': 'Not enough stock available'})
            cart_item.quantity += 1
        else:
            cart_item = CartItem(user_id=current_user.id, book_id=book_id, quantity=1)
            db.session.add(cart_item)
            
        db.session.commit()
        log_user_activity(current_user, 'cart_add', f'Added book #{book_id} to cart')
        
        count = CartItem.query.filter_by(user_id=current_user.id).with_entities(func.sum(CartItem.quantity)).scalar() or 0
        return jsonify({'success': True, 'count': int(count)})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in add_to_cart: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to add item to cart'}), 500

@cart.route('/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    try:
        data = request.get_json()
        if not data or 'quantity' not in data:
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400

        quantity = int(data['quantity'])
        if quantity < 0:
            return jsonify({'success': False, 'error': 'Invalid quantity'}), 400

        cart_item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
        
        if quantity > cart_item.book.stock:
            return jsonify({'success': False, 'error': 'Not enough stock available'})
        
        if quantity == 0:
            db.session.delete(cart_item)
        else:
            cart_item.quantity = quantity
            
        db.session.commit()
        log_user_activity(current_user, 'cart_update', f'Updated quantity for book #{cart_item.book_id}')
        
        # Calculate new total
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        total = sum(item.total for item in cart_items)
        count = sum(item.quantity for item in cart_items)
        
        return jsonify({
            'success': True, 
            'count': count,
            'total': total
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating cart: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to update cart'}), 500

@cart.route('/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    try:
        cart_item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
        db.session.delete(cart_item)
        db.session.commit()
        
        log_user_activity(current_user, 'cart_remove', f'Removed book #{cart_item.book_id} from cart')
        
        # Get updated cart count
        count = CartItem.query.filter_by(user_id=current_user.id).with_entities(func.sum(CartItem.quantity)).scalar() or 0
        return jsonify({'success': True, 'count': int(count)})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing item from cart: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to remove item from cart'}), 500
