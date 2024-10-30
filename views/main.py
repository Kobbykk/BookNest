from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from models import Book, Order
from app import db

main = Blueprint('main', __name__)

@main.route('/')
def index():
    books = Book.query.all()
    return render_template('index.html', books=books)

@main.route('/book/<int:book_id>')
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template('books/detail.html', book=book)

@main.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('orders/history.html', orders=user_orders)
