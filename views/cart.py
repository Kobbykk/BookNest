from flask import Blueprint, jsonify, render_template, session, request, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Book, Order, OrderItem
from app import db
import stripe
import os

cart = Blueprint('cart', __name__)

@cart.route('/cart/count')
def get_cart_count():
    try:
        cart_data = session.get('cart', {})
        # Initialize count as 0
        count = 0
        # Only sum if cart exists and has items
        if cart_data and len(cart_data) > 0:
            count = sum(int(val) for val in cart_data.values())
        return jsonify({'count': count, 'success': True})
    except Exception as e:
        current_app.logger.error(f'Error getting cart count: {str(e)}')
        return jsonify({'count': 0, 'success': False, 'error': str(e)})

@cart.route('/cart')
@login_required
def view_cart():
    cart_data = session.get('cart', {})
    cart_items = []
    total = 0
    
    for book_id, quantity in cart_data.items():
        book = Book.query.get(int(book_id))
        if book:
            item_total = book.price * quantity
            cart_items.append({
                'book': book,
                'quantity': quantity,
                'total': item_total
            })
            total += item_total
    
    return render_template('cart/cart.html', cart_items=cart_items, total=total)

@cart.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    try:
        cart_data = session.get('cart', {})
        book_id = str(request.json['book_id'])
        quantity = int(request.json['quantity'])
        
        # Validate book exists
        book = Book.query.get(int(book_id))
        if not book:
            return jsonify({'success': False, 'error': 'Book not found'}), 404
        
        if book_id in cart_data:
            cart_data[book_id] += quantity
        else:
            cart_data[book_id] = quantity
        
        session['cart'] = cart_data
        count = sum(int(val) for val in cart_data.values()) if cart_data and cart_data.values() else 0
        return jsonify({'success': True, 'cart_count': count})
    except Exception as e:
        current_app.logger.error(f'Error adding to cart: {str(e)}')
        return jsonify({'success': False, 'error': 'Failed to add item to cart'}), 500

@cart.route('/cart/update', methods=['POST'])
@login_required
def update_cart():
    try:
        cart_data = session.get('cart', {})
        book_id = str(request.json['book_id'])
        quantity = int(request.json['quantity'])
        
        if quantity > 0:
            cart_data[book_id] = quantity
        else:
            cart_data.pop(book_id, None)
        
        session['cart'] = cart_data
        count = sum(int(val) for val in cart_data.values()) if cart_data and cart_data.values() else 0
        return jsonify({'success': True, 'cart_count': count})
    except Exception as e:
        current_app.logger.error(f'Error updating cart: {str(e)}')
        return jsonify({'success': False, 'error': 'Failed to update cart'}), 500

@cart.route('/cart/checkout', methods=['GET'])
@login_required
def checkout():
    cart_data = session.get('cart', {})
    if not cart_data:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('cart.view_cart'))
    
    cart_items = []
    total = 0
    
    for book_id, quantity in cart_data.items():
        book = Book.query.get(int(book_id))
        if book:
            item_total = book.price * quantity
            cart_items.append({
                'book': book,
                'quantity': quantity,
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
        cart_data = session.get('cart', {})
        
        if not cart_data:
            return jsonify({'success': False, 'error': 'Cart is empty'})
        
        total = 0
        order_items = []
        
        # Calculate total and prepare order items
        for book_id, quantity in cart_data.items():
            book = Book.query.get(int(book_id))
            if book:
                if book.stock < quantity:
                    return jsonify({'success': False, 'error': f'Insufficient stock for {book.title}'})
                item_total = book.price * quantity
                total += item_total
                order_items.append({
                    'book': book,
                    'quantity': quantity,
                    'price': book.price
                })
        
        # Create order first to get the order ID
        order = Order(user_id=current_user.id, total=total, status='pending')
        db.session.add(order)
        db.session.flush()  # This will assign an ID to the order

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
        
        # Clear the cart
        session['cart'] = {}
        db.session.commit()
        
        return jsonify({
            'client_secret': intent.client_secret,
            'success': True
        })
            
    except stripe.error.StripeError as e:
        current_app.logger.error(f'Stripe error: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        })
    except Exception as e:
        current_app.logger.error(f'Payment processing error: {str(e)}')
        return jsonify({
            'success': False,
            'error': str(e)
        })

@cart.route('/payment/success')
@login_required
def payment_success():
    payment_intent_id = request.args.get('payment_intent')
    if payment_intent_id:
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            if intent.status == 'succeeded':
                flash('Payment successful!', 'success')
            else:
                flash('Payment was not completed.', 'error')
        except stripe.error.StripeError as e:
            flash('An error occurred while processing your payment.', 'error')
    return redirect(url_for('main.orders'))
