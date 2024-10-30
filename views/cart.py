from flask import Blueprint, jsonify, render_template, session, request, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Book, Order, OrderItem
from app import db
import stripe
import os

cart = Blueprint('cart', __name__)

@cart.route('/cart/count')
@login_required
def get_cart_count():
    cart_data = session.get('cart', {})
    count = sum(cart_data.values())
    return jsonify({'count': count})

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
        return jsonify({'success': True, 'cart_count': sum(cart_data.values())})
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
        return jsonify({'success': True, 'cart_count': sum(cart_data.values())})
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
        
        # Create payment intent
        payment_method_id = request.json.get('payment_method_id')
        if not payment_method_id:
            return jsonify({'success': False, 'error': 'Payment method not provided'})
        
        # Amount needs to be in cents
        amount = int(total * 100)
        
        # Create and confirm the payment intent
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='usd',
            payment_method=payment_method_id,
            confirmation_method='manual',
            confirm=True,
        )
        
        if intent.status == 'succeeded':
            # Create order
            order = Order(user_id=current_user.id, total=total, status='pending')
            db.session.add(order)
            db.session.flush()
            
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
                'success': True,
                'redirect_url': url_for('main.orders')
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Payment failed'
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
            'error': 'An error occurred while processing your payment'
        })
