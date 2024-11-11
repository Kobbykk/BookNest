from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, session
from flask_login import login_required, current_user
from models import CartItem, Book, Order, OrderItem, db
from utils.activity_logger import log_user_activity
from sqlalchemy import func
import stripe
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
cart = Blueprint('cart', __name__, url_prefix='/cart')

@cart.before_request
def require_login():
    """Ensure all cart routes require authentication"""
    if not current_user.is_authenticated:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Authentication required', 'redirect': url_for('auth.login')}), 401
        # Store the full path (including query parameters) in session for post-login redirect
        session['next'] = request.full_path
        return redirect(url_for('auth.login'))

@cart.route('/')
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
def checkout():
    try:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            flash('Your cart is empty.', 'warning')
            return redirect(url_for('main.index'))
            
        total = sum(item.total for item in cart_items)
        stripe_key = current_app.config.get('STRIPE_PUBLISHABLE_KEY')
        if not stripe_key:
            flash('Payment system is not properly configured.', 'danger')
            return redirect(url_for('cart.view_cart'))
            
        return render_template('cart/checkout.html', 
                             cart_items=cart_items,
                             total=total,
                             stripe_publishable_key=stripe_key)
    except Exception as e:
        logger.error(f"Error in checkout: {str(e)}")
        flash('An error occurred while processing your request.', 'danger')
        return redirect(url_for('main.index'))

@cart.route('/create-payment-intent', methods=['POST'])
def create_payment_intent():
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Invalid request format'}), 400

        stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
        if not stripe.api_key:
            logger.error("Stripe secret key not configured")
            return jsonify({'success': False, 'error': 'Payment system not properly configured'}), 500

        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            return jsonify({'success': False, 'error': 'Cart is empty'}), 400

        total = sum(item.total for item in cart_items)
        amount = int(total * 100)  # Convert to cents for Stripe

        # Create payment intent
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency='usd',
                metadata={
                    'user_id': current_user.id,
                    'email': current_user.email
                }
            )
            return jsonify({
                'success': True,
                'clientSecret': intent.client_secret
            })
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 400

    except Exception as e:
        logger.error(f"Error creating payment intent: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to initialize payment'}), 500

@cart.route('/payment-complete')
def payment_complete():
    try:
        payment_intent_id = request.args.get('payment_intent')
        if not payment_intent_id:
            flash('Invalid payment session.', 'danger')
            return redirect(url_for('cart.checkout'))

        stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {str(e)}")
            flash('Failed to verify payment.', 'danger')
            return redirect(url_for('cart.checkout'))

        if payment_intent.status != 'succeeded':
            flash('Payment was not successful.', 'danger')
            return redirect(url_for('cart.checkout'))

        # Create order
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        total = sum(item.total for item in cart_items)

        order = Order(
            user_id=current_user.id,
            total=total,
            status='processing',
            payment_intent_id=payment_intent_id,
            payment_status='paid',
            payment_method='card',
            payment_date=datetime.utcnow()
        )

        # Add order items and update stock
        for cart_item in cart_items:
            order_item = OrderItem(
                book_id=cart_item.book_id,
                quantity=cart_item.quantity,
                price=cart_item.book.price
            )
            order.items.append(order_item)
            
            # Update stock
            cart_item.book.stock -= cart_item.quantity
            if cart_item.book.stock < 0:
                db.session.rollback()
                flash('Some items in your cart are no longer available.', 'danger')
                return redirect(url_for('cart.view_cart'))

        # Clear cart
        for item in cart_items:
            db.session.delete(item)

        db.session.add(order)
        db.session.commit()

        log_user_activity(current_user, 'order_created', f'Created order #{order.id}')
        flash('Thank you for your purchase! Your order has been placed.', 'success')
        return redirect(url_for('main.orders'))

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error completing payment: {str(e)}")
        flash('An error occurred while processing your payment.', 'danger')
        return redirect(url_for('cart.checkout'))

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
def add_to_cart():
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Invalid request format'}), 400
            
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
def update_cart(item_id):
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Invalid request format'}), 400
            
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
