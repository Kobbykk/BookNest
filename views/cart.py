from flask import Blueprint, jsonify, render_template, session, request, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Book, Order, OrderItem, CartItem
from app import db
import stripe
import os
from sqlalchemy import func
from utils.email import send_order_status_email
from datetime import datetime
from utils.activity_logger import log_user_activity

cart = Blueprint('cart', __name__, url_prefix='/cart')

@cart.route('/count')
def get_cart_count():
    try:
        if not current_user.is_authenticated:
            return jsonify({'success': True, 'count': 0})
            
        count = CartItem.query.filter_by(user_id=current_user.id).count()
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        current_app.logger.error(f'Error getting cart count: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@cart.route('/view_cart')
@login_required
def view_cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.total for item in cart_items)
    return render_template('cart/cart.html', cart_items=cart_items, total=total)

@cart.route('/add', methods=['POST'])
@login_required
def add_to_cart():
    try:
        data = request.get_json()
        book_id = data.get('book_id')
        quantity = data.get('quantity', 1)
        
        if not book_id:
            return jsonify({'success': False, 'error': 'Book ID is required'}), 400
            
        book = Book.query.get_or_404(book_id)
        if book.stock < quantity:
            return jsonify({'success': False, 'error': 'Insufficient stock'}), 400
            
        cart_item = CartItem.query.filter_by(user_id=current_user.id, book_id=book_id).first()
        
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = CartItem(user_id=current_user.id, book_id=book_id, quantity=quantity)
            db.session.add(cart_item)
                
        db.session.commit()
        log_user_activity(current_user, 'cart_add', f'Added {quantity} copies of {book.title} to cart')
        
        cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
        return jsonify({'success': True, 'cart_count': cart_count})
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error adding to cart: {str(e)}')
        return jsonify({'success': False, 'error': 'Failed to add item to cart'}), 500

@cart.route('/update', methods=['POST'])
@login_required
def update_cart():
    try:
        data = request.get_json()
        book_id = data.get('book_id')
        quantity = data.get('quantity', 0)
        
        if not book_id:
            return jsonify({'success': False, 'error': 'Book ID is required'}), 400
            
        cart_item = CartItem.query.filter_by(user_id=current_user.id, book_id=book_id).first()
        if not cart_item:
            return jsonify({'success': False, 'error': 'Item not found in cart'}), 404
            
        book = Book.query.get_or_404(book_id)
        if quantity <= 0:
            db.session.delete(cart_item)
            log_user_activity(current_user, 'cart_remove', f'Removed {book.title} from cart')
        else:
            if book.stock < quantity:
                return jsonify({'success': False, 'error': 'Insufficient stock'}), 400
            cart_item.quantity = quantity
            log_user_activity(current_user, 'cart_update', f'Updated quantity of {book.title} to {quantity}')
                
        db.session.commit()
        cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
        return jsonify({'success': True, 'cart_count': cart_count})
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error updating cart: {str(e)}')
        return jsonify({'success': False, 'error': 'Failed to update cart'}), 500