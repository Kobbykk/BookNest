from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Book, Review, Order
from werkzeug.security import generate_password_hash
from sqlalchemy import func
from app import db
from forms import ReviewForm, ProfileUpdateForm

main = Blueprint('main', __name__)

@main.route('/')
@main.route('/home')
def index():
    books = Book.query.all()
    # Get categories for the filter dropdown
    categories = ['All Categories'] + [cat[0] for cat in Book.query.with_entities(Book.category).distinct() if cat[0]]
    
    # Get recommendations if user is authenticated
    recommendations = []
    search_query = request.args.get('search', '')
    current_category = request.args.get('category', 'All Categories')
    
    query = Book.query
    
    if search_query:
        query = query.filter(
            (Book.title.ilike(f'%{search_query}%')) |
            (Book.author.ilike(f'%{search_query}%')) |
            (Book.description.ilike(f'%{search_query}%'))
        )
    
    if current_category and current_category != 'All Categories':
        query = query.filter_by(category=current_category)
    
    books = query.all()
    
    return render_template('index.html', 
                         books=books,
                         categories=categories,
                         recommendations=recommendations,
                         search_query=search_query,
                         current_category=current_category)

@main.route('/book/<int:book_id>')
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    form = ReviewForm()
    similar_books = Book.query.filter(Book.category == book.category, 
                                    Book.id != book.id).limit(3).all()
    return render_template('books/detail.html', book=book, similar_books=similar_books, form=form)

@main.route('/book/<int:book_id>/review', methods=['POST'])
@login_required
def add_review(book_id):
    form = ReviewForm()
    if form.validate_on_submit():
        # Check if user has already reviewed this book
        existing_review = Review.query.filter_by(
            user_id=current_user.id,
            book_id=book_id
        ).first()
        
        if existing_review:
            flash('You have already reviewed this book!', 'warning')
        else:
            review = Review(
                user_id=current_user.id,
                book_id=book_id,
                rating=form.rating.data,
                comment=form.comment.data
            )
            db.session.add(review)
            db.session.commit()
            flash('Your review has been added!', 'success')
    return redirect(url_for('main.book_detail', book_id=book_id))

@main.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders/history.html', orders=user_orders)

@main.route('/profile')
@login_required
def profile():
    form = ProfileUpdateForm(obj=current_user)
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    user_reviews = Review.query.filter_by(user_id=current_user.id).order_by(Review.created_at.desc()).all()
    return render_template('profile/profile.html', form=form, orders=user_orders, reviews=user_reviews)

@main.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    form = ProfileUpdateForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        if form.email.data:
            current_user.email = form.email.data.lower()
        if form.new_password.data:
            current_user.password_hash = generate_password_hash(form.new_password.data)
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    return redirect(url_for('main.profile'))
