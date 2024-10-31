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

@cart.route('/checkout')
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('cart.view_cart'))
    
    total = sum(item.total for item in cart_items)
    return render_template('cart/checkout.html', 
                         cart_items=cart_items,
                         total=total,
                         stripe_publishable_key=os.environ.get('STRIPE_PUBLISHABLE_KEY'))

@cart.route('/create-payment-intent', methods=['POST'])
@login_required
def create_payment_intent():
    try:
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        
        if not cart_items:
            return jsonify({'success': False, 'error': 'Cart is empty'}), 400
        
        total = sum(item.total for item in cart_items)
        amount = int(total * 100)  # Convert to cents
        
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='usd',
            automatic_payment_methods={
                'enabled': True,
            }
        )
        
        return jsonify({
            'success': True,
            'clientSecret': intent.client_secret
        })
    except Exception as e:
        current_app.logger.error(f'Error creating payment intent: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@cart.route('/payment-success')
@login_required
def payment_success():
    try:
        payment_intent_id = request.args.get('payment_intent')
        if not payment_intent_id:
            flash('Invalid payment session.', 'danger')
            return redirect(url_for('cart.checkout'))
        
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if payment_intent.status != 'succeeded':
            flash('Payment was not successful.', 'danger')
            return redirect(url_for('cart.checkout'))
        
        # Get cart items
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            flash('Your cart is empty.', 'warning')
            return redirect(url_for('cart.view_cart'))
        
        # Calculate total
        total = sum(item.total for item in cart_items)
        
        # Create order
        order = Order(
            user_id=current_user.id,
            total=total,
            status='processing',
            payment_intent_id=payment_intent_id,
            payment_status='completed',
            payment_method='card',
            payment_date=datetime.utcnow()
        )
        db.session.add(order)
        
        # Create order items and update stock
        for cart_item in cart_items:
            order_item = OrderItem(
                order=order,
                book_id=cart_item.book_id,
                quantity=cart_item.quantity,
                price=cart_item.book.price
            )
            db.session.add(order_item)
            
            # Update book stock
            book = cart_item.book
            book.stock -= cart_item.quantity
            
            # Delete cart item
            db.session.delete(cart_item)
        
        db.session.commit()
        
        # Send confirmation email
        try:
            send_order_status_email(current_user.email, order.id, order.status, order.items)
        except Exception as e:
            current_app.logger.error(f'Error sending order confirmation email: {str(e)}')
        
        log_user_activity(current_user, 'order_placed', f'Order #{order.id} placed successfully')
        flash('Your order has been placed successfully!', 'success')
        return redirect(url_for('main.orders'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error processing payment success: {str(e)}')
        flash('An error occurred while processing your order.', 'danger')
        return redirect(url_for('cart.checkout'))
