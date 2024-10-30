from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from sqlalchemy import or_
from models import Book, Order, Review
from forms import ReviewForm
from app import db

main = Blueprint('main', __name__)

@main.route('/')
def index():
    search_query = request.args.get('search', '').strip()
    category = request.args.get('category', 'All')
    
    # Get all unique categories for the filter dropdown
    categories = ['All'] + [cat[0] for cat in db.session.query(Book.category).distinct().order_by(Book.category)]
    
    # Build the query
    query = Book.query
    
    # Apply category filter if not 'All'
    if category != 'All':
        query = query.filter(Book.category == category)
    
    # Apply search filter if there's a search query
    if search_query:
        query = query.filter(
            or_(
                Book.title.ilike(f'%{search_query}%'),
                Book.author.ilike(f'%{search_query}%'),
                Book.description.ilike(f'%{search_query}%')
            )
        )
    
    # Get the filtered books
    books = query.all()
    
    return render_template('index.html', 
                         books=books, 
                         categories=categories, 
                         current_category=category,
                         search_query=search_query)

@main.route('/book/<int:book_id>', methods=['GET'])
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    form = ReviewForm()
    return render_template('books/detail.html', book=book, form=form)

@main.route('/book/<int:book_id>/review', methods=['POST'])
@login_required
def add_review(book_id):
    book = Book.query.get_or_404(book_id)
    form = ReviewForm()
    
    if form.validate_on_submit():
        # Check if user has already reviewed this book
        existing_review = Review.query.filter_by(user_id=current_user.id, book_id=book_id).first()
        if existing_review:
            flash('You have already reviewed this book.', 'warning')
            return redirect(url_for('main.book_detail', book_id=book_id))
        
        review = Review(
            user_id=current_user.id,
            book_id=book_id,
            rating=form.rating.data,
            comment=form.comment.data
        )
        db.session.add(review)
        db.session.commit()
        flash('Your review has been added successfully!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
    
    return redirect(url_for('main.book_detail', book_id=book_id))

@main.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('orders/history.html', orders=user_orders)
