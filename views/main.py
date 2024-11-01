from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db, Book, Review, Order, OrderItem, Wishlist, ReadingList, ReadingListItem
from werkzeug.security import generate_password_hash
from sqlalchemy import func, or_
from forms import ReviewForm, ProfileUpdateForm
from utils.activity_logger import log_user_activity

main = Blueprint('main', __name__)

@main.route('/')
@main.route('/home')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    # Get featured books for carousel
    featured_books = Book.query.filter_by(is_featured=True).limit(5).all()
    
    # Get categories for the filter dropdown
    categories = ['All Categories'] + [cat[0] for cat in Book.query.with_entities(Book.category).distinct() if cat[0]]
    
    # Get filter parameters
    search_query = request.args.get('search', '')
    current_category = request.args.get('category', 'All Categories')
    sort_by = request.args.get('sort', 'relevance')
    price_range = request.args.get('price_range', '')
    
    # Build the query
    query = Book.query
    
    # Apply search filter
    if search_query:
        search_terms = search_query.split()
        conditions = []
        for term in search_terms:
            conditions.append(or_(
                Book.title.ilike(f'%{term}%'),
                Book.author.ilike(f'%{term}%'),
                Book.description.ilike(f'%{term}%'),
                Book.tags.ilike(f'%{term}%')
            ))
        query = query.filter(or_(*conditions))
    
    # Apply category filter
    if current_category and current_category != 'All Categories':
        query = query.filter_by(category=current_category)
    
    # Apply price range filter
    if price_range:
        min_price, max_price = map(float, price_range.split('-'))
        query = query.filter(Book.price >= min_price, Book.price <= max_price)
    
    # Apply sorting
    if sort_by == 'price_low':
        query = query.order_by(Book.price.asc())
    elif sort_by == 'price_high':
        query = query.order_by(Book.price.desc())
    elif sort_by == 'newest':
        query = query.order_by(Book.created_at.desc())
    elif sort_by == 'rating':
        query = query.order_by(Book.average_rating.desc())

    # Paginate results
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    books = pagination.items
    
    return render_template('index.html',
                         books=books,
                         pagination=pagination,
                         categories=categories,
                         featured_books=featured_books,
                         search_query=search_query,
                         current_category=current_category,
                         sort_by=sort_by,
                         price_range=price_range)

# Rest of the routes remain the same...
