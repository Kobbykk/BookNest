from flask import Blueprint, jsonify, render_template, session, request, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Book, Order, OrderItem, CartItem
from app import db
import stripe
import os
from sqlalchemy import func
from utils.email import send_order_status_email
from datetime import datetime

cart = Blueprint('cart', __name__)

@cart.route('/count')
@login_required
def get_cart_count():
    try:
        count = CartItem.query.filter_by(user_id=current_user.id).count()
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        current_app.logger.error(f'Error getting cart count: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@cart.route('/view_cart')
@login_required
def view_cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.book.price * item.quantity for item in cart_items)
    return render_template('cart/cart.html', cart_items=cart_items, total=total)

@cart.route('/add', methods=['POST'])
@login_required
def add_to_cart():
    data = request.get_json()
    book_id = data.get('book_id')
    quantity = data.get('quantity', 1)
    
    if not book_id:
        return jsonify({'error': 'Book ID is required'}), 400
        
    book = Book.query.get_or_404(book_id)
    if book.stock < quantity:
        return jsonify({'error': 'Insufficient stock'}), 400
        
    cart_item = CartItem.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    
    try:
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = CartItem(user_id=current_user.id, book_id=book_id, quantity=quantity)
            db.session.add(cart_item)
            
        db.session.commit()
        cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
        return jsonify({'success': True, 'cart_count': cart_count})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error adding to cart: {str(e)}')
        return jsonify({'error': 'Failed to add item to cart'}), 500

@cart.route('/update', methods=['POST'])
@login_required
def update_cart():
    data = request.get_json()
    book_id = data.get('book_id')
    quantity = data.get('quantity', 0)
    
    if not book_id:
        return jsonify({'error': 'Book ID is required'}), 400
        
    cart_item = CartItem.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if not cart_item:
        return jsonify({'error': 'Item not found in cart'}), 404
        
    try:
        if quantity <= 0:
            db.session.delete(cart_item)
        else:
            if cart_item.book.stock < quantity:
                return jsonify({'error': 'Insufficient stock'}), 400
            cart_item.quantity = quantity
            
        db.session.commit()
        cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
        return jsonify({'success': True, 'cart_count': cart_count})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error updating cart: {str(e)}')
        return jsonify({'error': 'Failed to update cart'}), 500

@cart.route('/checkout')
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('main.index'))
        
    total = sum(item.book.price * item.quantity for item in cart_items)
    stripe_publishable_key = os.environ.get('STRIPE_PUBLISHABLE_KEY')
    
    if not stripe_publishable_key:
        flash('Payment system is not configured.', 'error')
        return redirect(url_for('cart.view_cart'))
        
    return render_template('cart/checkout.html',
                         cart_items=cart_items,
                         total=total,
                         stripe_publishable_key=stripe_publishable_key)

@cart.route('/create-payment-intent', methods=['POST'])
@login_required
def create_payment_intent():
    try:
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
        if not stripe.api_key:
            current_app.logger.error('Stripe secret key not configured')
            return jsonify({'error': 'Payment system is not configured'}), 500
            
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            return jsonify({'error': 'Cart is empty'}), 400
        
        # Calculate total and validate stock in a transaction
        try:
            total = 0
            with db.session.begin_nested():
                for item in cart_items:
                    if item.book.stock < item.quantity:
                        return jsonify({'error': f'Insufficient stock for {item.book.title}'}), 400
                    total += item.book.price * item.quantity
                
                # Create order first
                order = Order(
                    user_id=current_user.id,
                    total=total,
                    status='pending',
                    payment_status='pending'
                )
                db.session.add(order)
                db.session.flush()
                
                # Create order items
                for cart_item in cart_items:
                    order_item = OrderItem(
                        order_id=order.id,
                        book_id=cart_item.book_id,
                        quantity=cart_item.quantity,
                        price=cart_item.book.price
                    )
                    db.session.add(order_item)
                
                # Create payment intent
                try:
                    intent = stripe.PaymentIntent.create(
                        amount=int(total * 100),  # Convert to cents
                        currency='usd',
                        metadata={
                            'order_id': str(order.id),
                            'user_id': str(current_user.id)
                        }
                    )
                    
                    # Update order with payment intent
                    order.payment_intent_id = intent.id
                    db.session.commit()
                    
                    return jsonify({
                        'clientSecret': intent.client_secret,
                        'orderId': order.id
                    })
                    
                except stripe.error.StripeError as e:
                    current_app.logger.error(f'Stripe error: {str(e)}')
                    db.session.rollback()
                    return jsonify({'error': str(e)}), 400
                    
        except Exception as e:
            current_app.logger.error(f'Database error: {str(e)}')
            db.session.rollback()
            return jsonify({'error': 'Error creating order'}), 500
            
    except Exception as e:
        current_app.logger.error(f'Unexpected error: {str(e)}')
        return jsonify({'error': 'An unexpected error occurred'}), 500

@cart.route('/payment/success')
@login_required
def payment_success():
    payment_intent_id = request.args.get('payment_intent')
    
    if not payment_intent_id:
        flash('Invalid payment session.', 'error')
        return redirect(url_for('cart.checkout'))
    
    try:
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
        if not stripe.api_key:
            flash('Payment system is not configured.', 'error')
            return redirect(url_for('cart.checkout'))
            
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        # Find order by payment intent ID
        order = Order.query.filter_by(payment_intent_id=payment_intent_id).first()
        if not order:
            flash('Order not found.', 'error')
            return redirect(url_for('cart.checkout'))
        
        if intent.status == 'succeeded':
            try:
                # Update order status
                order.status = 'completed'
                order.payment_status = 'paid'
                order.payment_date = datetime.utcnow()
                order.payment_method = intent.payment_method_types[0]
                
                # Update book stock
                for item in order.items:
                    if item.book.stock < item.quantity:
                        raise ValueError(f'Insufficient stock for {item.book.title}')
                    item.book.stock -= item.quantity
                
                # Clear cart
                CartItem.query.filter_by(user_id=current_user.id).delete()
                db.session.commit()
                
                # Send confirmation email
                try:
                    send_order_status_email(current_user.email, order.id, "completed", order.items)
                except Exception as e:
                    current_app.logger.error(f'Error sending confirmation email: {str(e)}')
                
                flash('Payment successful! Your order has been confirmed.', 'success')
                return redirect(url_for('main.orders'))
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f'Error processing successful payment: {str(e)}')
                flash('Error processing your order. Please contact support.', 'error')
                return redirect(url_for('cart.checkout'))
        else:
            order.status = 'payment_failed'
            order.payment_status = 'failed'
            db.session.commit()
            
            flash('Payment was not completed successfully.', 'error')
            return redirect(url_for('cart.checkout'))
            
    except stripe.error.StripeError as e:
        current_app.logger.error(f'Stripe error in success callback: {str(e)}')
        flash(f'Payment error: {str(e)}', 'error')
        return redirect(url_for('cart.checkout'))
    except Exception as e:
        current_app.logger.error(f'Error in success callback: {str(e)}')
        flash('An unexpected error occurred.', 'error')
        return redirect(url_for('cart.checkout'))
