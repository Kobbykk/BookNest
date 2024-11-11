from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from models import db, Book, Review, Order, OrderItem, Wishlist, ReadingList, ReadingListItem, UserActivity
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, or_
from forms import ReviewForm, ProfileUpdateForm
from utils.activity_logger import log_user_activity

main = Blueprint('main', __name__)

@main.route('/')
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

@main.route('/book/<int:book_id>')
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    form = ReviewForm()
    return render_template('books/detail.html', book=book, form=form)

@main.route('/profile')
@login_required
def profile():
    try:
        activities = UserActivity.query.filter_by(user_id=current_user.id)\
                           .order_by(UserActivity.timestamp.desc())\
                           .limit(5).all()
        return render_template('profile/profile.html', activities=activities)
    except Exception as e:
        flash('An error occurred while loading your profile.', 'danger')
        return redirect(url_for('main.index'))

@main.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    try:
        form = ProfileUpdateForm(obj=current_user)
        if form.validate_on_submit():
            if not current_user.check_password(form.current_password.data):
                flash('Current password is incorrect.', 'danger')
                return render_template('profile/settings.html', form=form)
            
            current_user.username = form.username.data
            current_user.email = form.email.data.lower()
            
            if form.new_password.data:
                current_user.password_hash = generate_password_hash(form.new_password.data)
            
            try:
                db.session.commit()
                log_user_activity(current_user, 'profile_update', 'Updated profile settings')
                flash('Your profile has been updated!', 'success')
                return redirect(url_for('main.profile'))
            except Exception as e:
                db.session.rollback()
                flash('An error occurred while updating your profile.', 'danger')
        
        return render_template('profile/settings.html', form=form)
    except Exception as e:
        flash('An error occurred while accessing settings.', 'danger')
        return redirect(url_for('main.profile'))

@main.route('/orders')
@login_required
def orders():
    try:
        user_orders = Order.query.filter_by(user_id=current_user.id)\
                          .order_by(Order.created_at.desc()).all()
        return render_template('orders/list.html', orders=user_orders)
    except Exception as e:
        flash('An error occurred while loading your orders.', 'danger')
        return redirect(url_for('main.profile'))

@main.route('/add_review/<int:book_id>', methods=['POST'])
@login_required
def add_review(book_id):
    try:
        form = ReviewForm()
        if form.validate_on_submit():
            # Check if user has already reviewed this book
            existing_review = Review.query.filter_by(
                user_id=current_user.id,
                book_id=book_id
            ).first()
            
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
            
            log_user_activity(current_user, 'review_add', f'Added review for book #{book_id}')
            flash('Your review has been added!', 'success')
        
        return redirect(url_for('main.book_detail', book_id=book_id))
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while adding your review.', 'danger')
        return redirect(url_for('main.book_detail', book_id=book_id))
