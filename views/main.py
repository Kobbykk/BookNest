from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from models import Book, Order, Review, OrderItem, Category
from forms import ReviewForm
from app import db
from collections import Counter

main = Blueprint('main', __name__)

def get_recommendations(user_id, limit=5):
    """Get book recommendations based on user's purchase history"""
    if not user_id:
        return Book.query.order_by(func.random()).limit(limit).all()
    
    # Get books the user has purchased
    user_purchases = (db.session.query(Book.category)
        .join(OrderItem, Book.id == OrderItem.book_id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.user_id == user_id)
        .all())
    
    # If user has no purchases, return random books
    if not user_purchases:
        return Book.query.order_by(func.random()).limit(limit).all()
    
    # Get most purchased categories by the user
    categories = [cat[0] for cat in user_purchases]
    top_categories = [cat for cat, _ in Counter(categories).most_common(2)]
    
    # Get books from user's preferred categories that they haven't purchased
    purchased_books = (db.session.query(Book.id)
        .join(OrderItem, Book.id == OrderItem.book_id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.user_id == user_id)
        .all())
    purchased_ids = [book[0] for book in purchased_books]
    
    recommendations = (Book.query
        .filter(Book.category.in_(top_categories))
        .filter(~Book.id.in_(purchased_ids))
        .order_by(func.random())
        .limit(limit)
        .all())
    
    # If not enough recommendations, add some random books
    if len(recommendations) < limit:
        additional = (Book.query
            .filter(~Book.id.in_(purchased_ids))
            .filter(~Book.id.in_([book.id for book in recommendations]))
            .order_by(func.random())
            .limit(limit - len(recommendations))
            .all())
        recommendations.extend(additional)
    
    return recommendations

@main.route('/')
def index():
    search_query = request.args.get('search', '').strip()
    category = request.args.get('category', 'All')
    
    # Get all categories from the Category model
    categories = ['All'] + [cat.name for cat in Category.query.order_by(Category.display_order).all()]
    
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
    
    # Get recommendations for the current user
    recommendations = get_recommendations(current_user.id if current_user.is_authenticated else None)
    
    return render_template('index.html', 
                         books=books, 
                         categories=categories, 
                         current_category=category,
                         search_query=search_query,
                         recommendations=recommendations)

@main.route('/book/<int:book_id>', methods=['GET'])
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    form = ReviewForm()
    
    # Get recommendations based on the current book's category
    similar_books = (Book.query
        .filter(Book.category == book.category)
        .filter(Book.id != book.id)
        .order_by(func.random())
        .limit(3)
        .all())
    
    return render_template('books/detail.html', book=book, form=form, similar_books=similar_books)

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
