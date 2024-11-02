from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import CartItem, Book, Order, OrderItem
from extensions import db
from utils.activity_logger import log_user_activity
from sqlalchemy import func
import stripe
from datetime import datetime

cart = Blueprint('cart', __name__)

@cart.route('/cart/count')
@login_required
def get_cart_count():
    try:
        # Use coalesce to handle NULL values
        count = db.session.query(
            func.coalesce(func.sum(CartItem.quantity), 0)
        ).filter_by(user_id=current_user.id).scalar()
        
        return jsonify({'success': True, 'count': int(count)})
    except Exception as e:
        current_app.logger.error(f"Error getting cart count: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to fetch cart count'}), 500

@cart.route('/cart')
@login_required
def view_cart():
    try:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        total = sum(item.total for item in cart_items)
        return render_template('cart/cart.html', cart_items=cart_items, total=total)
    except Exception as e:
        current_app.logger.error(f"Error viewing cart: {str(e)}")
        flash('An error occurred while loading your cart.', 'danger')
        return redirect(url_for('main.index'))

@cart.route('/cart/checkout')
@login_required
def checkout():
    try:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            flash('Your cart is empty', 'warning')
            return redirect(url_for('cart.view_cart'))

        total = sum(item.total for item in cart_items)
        
        # Verify Stripe configuration
        stripe_publishable_key = current_app.config.get('STRIPE_PUBLISHABLE_KEY')
        if not stripe_publishable_key:
            current_app.logger.error("Stripe publishable key not configured")
            flash('Payment system is not properly configured', 'danger')
            return redirect(url_for('cart.view_cart'))

        # Verify stock availability with proper error messages
        for item in cart_items:
            if item.quantity > item.book.stock:
                flash(f'Not enough stock for "{item.book.title}" (Only {item.book.stock} available)', 'danger')
                return redirect(url_for('cart.view_cart'))

        return render_template('cart/checkout.html',
                             cart_items=cart_items,
                             total=total,
                             stripe_publishable_key=stripe_publishable_key)
    except Exception as e:
        current_app.logger.error(f"Error during checkout: {str(e)}")
        flash('An error occurred during checkout. Please try again.', 'danger')
        return redirect(url_for('cart.view_cart'))

@cart.route('/cart/create-payment-intent', methods=['POST'])
@login_required
def create_payment_intent():
    try:
        stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
        if not stripe.api_key:
            raise ValueError("Payment system is not properly configured")

        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            raise ValueError("Your cart is empty")

        # Calculate total and verify stock
        total = 0
        for item in cart_items:
            if item.quantity > item.book.stock:
                raise ValueError(f'Insufficient stock for "{item.book.title}"')
            total += item.book.price * item.quantity

        # Create payment intent with proper error handling
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(total * 100),  # Convert to cents
                currency='usd',
                metadata={
                    'user_id': str(current_user.id),
                    'email': current_user.email
                },
                automatic_payment_methods={
                    'enabled': True
                }
            )
            return jsonify({
                'success': True,
                'clientSecret': intent.client_secret
            })

        except stripe.error.CardError as e:
            return jsonify({
                'success': False,
                'error': e.error.message
            }), 400
        except stripe.error.InvalidRequestError as e:
            current_app.logger.error(f"Invalid request to Stripe API: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Invalid payment request'
            }), 400
        except stripe.error.AuthenticationError:
            current_app.logger.error("Stripe authentication failed")
            return jsonify({
                'success': False,
                'error': 'Payment service configuration error'
            }), 500
        except stripe.error.APIConnectionError:
            current_app.logger.error("Failed to connect to Stripe API")
            return jsonify({
                'success': False,
                'error': 'Unable to connect to payment service'
            }), 503
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe API error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Payment service error'
            }), 500

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error in payment intent creation: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500

@cart.route('/cart/payment-complete')
@login_required
def payment_complete():
    try:
        payment_intent_id = request.args.get('payment_intent')
        if not payment_intent_id:
            flash('Invalid payment session', 'danger')
            return redirect(url_for('cart.checkout'))

        stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        except stripe.error.StripeError as e:
            current_app.logger.error(f"Failed to retrieve payment intent: {str(e)}")
            flash('Failed to verify payment status', 'danger')
            return redirect(url_for('cart.checkout'))

        if payment_intent.status != 'succeeded':
            flash('Payment was not successful', 'danger')
            return redirect(url_for('cart.checkout'))

        if payment_intent.metadata.get('user_id') != str(current_user.id):
            flash('Invalid payment session', 'danger')
            return redirect(url_for('cart.checkout'))

        # Check for existing order
        existing_order = Order.query.filter_by(payment_intent_id=payment_intent_id).first()
        if existing_order:
            flash('Order has already been processed', 'info')
            return redirect(url_for('main.orders'))

        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            flash('Cart is empty', 'warning')
            return redirect(url_for('cart.view_cart'))

        # Create order with transaction
        try:
            total = sum(item.total for item in cart_items)
            order = Order(
                user_id=current_user.id,
                total=total,
                status='processing',
                payment_intent_id=payment_intent_id,
                payment_status='completed',
                payment_method='card',
                payment_date=datetime.utcnow()
            )

            # Verify stock one last time before completing order
            for cart_item in cart_items:
                if cart_item.quantity > cart_item.book.stock:
                    raise ValueError(f'Insufficient stock for "{cart_item.book.title}"')

                order_item = OrderItem(
                    book_id=cart_item.book_id,
                    quantity=cart_item.quantity,
                    price=cart_item.book.price
                )
                order.items.append(order_item)
                cart_item.book.stock -= cart_item.quantity
                db.session.delete(cart_item)

            db.session.add(order)
            db.session.commit()

            log_user_activity(current_user, 'order_created', f'Created order #{order.id}')
            flash('Order processed successfully!', 'success')
            return redirect(url_for('main.orders'))

        except ValueError as e:
            db.session.rollback()
            flash(str(e), 'danger')
            return redirect(url_for('cart.checkout'))

    except Exception as e:
        current_app.logger.error(f"Error during payment completion: {str(e)}")
        db.session.rollback()
        flash('An unexpected error occurred while processing your order', 'danger')
        return redirect(url_for('cart.checkout'))
