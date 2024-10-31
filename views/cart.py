from flask import Blueprint, jsonify, render_template, session, request, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Book, Order, OrderItem, CartItem
from app import db
import stripe
import os
from sqlalchemy import func
from utils.email import send_order_status_email

cart = Blueprint('cart', __name__)

@cart.route('/cart/count')
def get_cart_count():
    try:
        if not current_user.is_authenticated:
            return jsonify({'count': 0, 'success': True})
            
        count = CartItem.query.filter_by(user_id=current_user.id).with_entities(
            func.sum(CartItem.quantity)).scalar() or 0
        return jsonify({'count': count, 'success': True})
    except Exception as e:
        current_app.logger.error(f'Error getting cart count: {str(e)}')
        return jsonify({'count': 0, 'success': False, 'error': str(e)})

@cart.route('/cart')
@login_required
def view_cart():
    cart_items = []
    total = 0
    
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    
    for item in items:
        item_total = item.book.price * item.quantity
        cart_items.append({
            'book': item.book,
            'quantity': item.quantity,
            'total': item_total
        })
        total += item_total
    
    return render_template('cart/cart.html', cart_items=cart_items, total=total)

@cart.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    try:
        book_id = int(request.json['book_id'])
        quantity = int(request.json['quantity'])
        
        # Validate book exists
        book = Book.query.get(book_id)
        if not book:
            return jsonify({'success': False, 'error': 'Book not found'}), 404
        
        # Check if item already in cart
        cart_item = CartItem.query.filter_by(
            user_id=current_user.id,
            book_id=book_id
        ).first()
        
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = CartItem(
                user_id=current_user.id,
                book_id=book_id,
                quantity=quantity
            )
            db.session.add(cart_item)
        
        db.session.commit()
        
        # Get updated cart count
        count = CartItem.query.filter_by(user_id=current_user.id).with_entities(
            func.sum(CartItem.quantity)).scalar() or 0
            
        return jsonify({'success': True, 'cart_count': count})
    except Exception as e:
        current_app.logger.error(f'Error adding to cart: {str(e)}')
        return jsonify({'success': False, 'error': 'Failed to add item to cart'}), 500

@cart.route('/cart/update', methods=['POST'])
@login_required
def update_cart():
    try:
        book_id = int(request.json['book_id'])
        quantity = int(request.json['quantity'])
        
        cart_item = CartItem.query.filter_by(
            user_id=current_user.id,
            book_id=book_id
        ).first()
        
        if not cart_item:
            return jsonify({'success': False, 'error': 'Item not found in cart'}), 404
        
        if quantity > 0:
            cart_item.quantity = quantity
        else:
            db.session.delete(cart_item)
        
        db.session.commit()
        
        count = CartItem.query.filter_by(user_id=current_user.id).with_entities(
            func.sum(CartItem.quantity)).scalar() or 0
            
        return jsonify({'success': True, 'cart_count': count})
    except Exception as e:
        current_app.logger.error(f'Error updating cart: {str(e)}')
        return jsonify({'success': False, 'error': 'Failed to update cart'}), 500

@cart.route('/cart/checkout', methods=['GET'])
@login_required
def checkout():
    cart_items = []
    total = 0
    
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('cart.view_cart'))
    
    for item in items:
        item_total = item.book.price * item.quantity
        cart_items.append({
            'book': item.book,
            'quantity': item.quantity,
            'total': item_total
        })
        total += item_total
    
    stripe_publishable_key = os.environ.get('STRIPE_PUBLISHABLE_KEY')
    return render_template('cart/checkout.html', 
                         cart_items=cart_items, 
                         total=total,
                         stripe_publishable_key=stripe_publishable_key)

@cart.route('/cart/process-payment', methods=['POST'])
@login_required
def process_payment():
    try:
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        
        if not cart_items:
            return jsonify({'success': False, 'error': 'Cart is empty'})
        
        total = 0
        order_items = []
        
        for cart_item in cart_items:
            if cart_item.book.stock < cart_item.quantity:
                return jsonify({'success': False, 'error': f'Insufficient stock for {cart_item.book.title}'})
            item_total = cart_item.book.price * cart_item.quantity
            total += item_total
            order_items.append({
                'book': cart_item.book,
                'quantity': cart_item.quantity,
                'price': cart_item.book.price
            })
        
        # Create order
        order = Order(user_id=current_user.id, total=total, status='pending')
        db.session.add(order)
        db.session.flush()
        
        # Amount needs to be in cents
        amount = int(total * 100)
        
        # Create payment intent with return_url and allow_redirects
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='usd',
            automatic_payment_methods={
                'enabled': True,
                'allow_redirects': 'always'
            },
            metadata={
                'order_id': str(order.id)
            },
            return_url=url_for('cart.payment_success', _external=True)
        )
        
        # Create order items and update stock
        for item in order_items:
            order_item = OrderItem(
                order_id=order.id,
                book_id=item['book'].id,
                quantity=item['quantity'],
                price=item['price']
            )
            # Update book stock
            item['book'].stock -= item['quantity']
            db.session.add(order_item)
        
        # Clear user's cart
        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        return jsonify({
            'client_secret': intent.client_secret,
            'success': True
        })
    except Exception as e:
        current_app.logger.error(f'Payment processing error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})

@cart.route('/payment/success')
@login_required
def payment_success():
    payment_intent_id = request.args.get('payment_intent')
    if payment_intent_id:
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            if intent.status == 'succeeded':
                order_id = intent.metadata.get('order_id')
                if order_id:
                    order = Order.query.get(order_id)
                    if order:
                        order.status = 'completed'
                        db.session.commit()
                        # Send email notification
                        send_order_status_email(
                            current_user.email,
                            order.id,
                            'completed',
                            order.items
                        )
                flash('Payment successful! Your order has been confirmed.', 'success')
            else:
                flash('Payment was not completed.', 'error')
        except stripe.error.StripeError as e:
            flash('An error occurred while processing your payment.', 'error')
    return redirect(url_for('main.orders'))
