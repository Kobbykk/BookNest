from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Book, Review, Order
from werkzeug.security import generate_password_hash
from sqlalchemy import func
from app import db

main = Blueprint('main', __name__)

@main.route('/')
@main.route('/home')
def index():
    books = Book.query.all()
    # Get categories for the filter dropdown
    categories = [cat[0] for cat in Book.query.with_entities(Book.category).distinct()]
    
    # Get recommendations if user is authenticated
    recommendations = []
    search_query = ''
    current_category = 'All Categories'
    
    return render_template('index.html', 
                         books=books,
                         categories=categories,
                         recommendations=recommendations,
                         search_query=search_query,
                         current_category=current_category)

@main.route('/book/<int:book_id>')
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    similar_books = Book.query.filter(Book.category == book.category, 
                                    Book.id != book.id).limit(3).all()
    return render_template('books/detail.html', book=book, similar_books=similar_books)

@main.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders/history.html', orders=user_orders)

@main.route('/profile')
@login_required
def profile():
    from forms import ProfileUpdateForm
    form = ProfileUpdateForm(obj=current_user)
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    user_reviews = Review.query.filter_by(user_id=current_user.id).order_by(Review.created_at.desc()).all()
    return render_template('profile/profile.html', form=form, orders=user_orders, reviews=user_reviews)

@main.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    from forms import ProfileUpdateForm
    form = ProfileUpdateForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        if form.new_password.data:
            current_user.password_hash = generate_password_hash(form.new_password.data)
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    return redirect(url_for('main.profile'))
