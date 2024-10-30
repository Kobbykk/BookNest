from flask import Blueprint, jsonify, render_template, session, request
from flask_login import login_required, current_user
from models import Book

cart = Blueprint('cart', __name__)

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
    cart_data = session.get('cart', {})
    book_id = str(request.json['book_id'])
    quantity = int(request.json['quantity'])
    
    if book_id in cart_data:
        cart_data[book_id] += quantity
    else:
        cart_data[book_id] = quantity
    
    session['cart'] = cart_data
    return jsonify({'success': True, 'cart_count': sum(cart_data.values())})

@cart.route('/cart/update', methods=['POST'])
@login_required
def update_cart():
    cart_data = session.get('cart', {})
    book_id = str(request.json['book_id'])
    quantity = int(request.json['quantity'])
    
    if quantity > 0:
        cart_data[book_id] = quantity
    else:
        cart_data.pop(book_id, None)
    
    session['cart'] = cart_data
    return jsonify({'success': True})
