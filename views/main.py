from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import Book, Review, Order, OrderItem, Wishlist, ReadingList, ReadingListItem
from werkzeug.security import generate_password_hash
from sqlalchemy import func, or_
from app import db
from forms import ReviewForm, ProfileUpdateForm
from utils.activity_logger import log_user_activity

main = Blueprint('main', __name__)

@main.route('/')
@main.route('/home')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
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
    
    # Get recommendations if user is authenticated
    recommendations = []
    if current_user.is_authenticated:
        # Get user's purchase history categories using a corrected query
        purchased_categories = db.session.query(Book.category)\
            .join(OrderItem, Book.id == OrderItem.book_id)\
            .join(Order, Order.id == OrderItem.order_id)\
            .filter(Order.user_id == current_user.id)\
            .group_by(Book.category)\
            .all()
        
        if purchased_categories:
            categories_list = [cat[0] for cat in purchased_categories]
            recommendations = Book.query\
                .filter(Book.category.in_(categories_list))\
                .order_by(func.random())\
                .limit(4)\
                .all()
    
    # Paginate results
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    books = pagination.items
    
    return render_template('index.html',
                         books=books,
                         pagination=pagination,
                         categories=categories,
                         recommendations=recommendations,
                         search_query=search_query,
                         current_category=current_category,
                         sort_by=sort_by,
                         price_range=price_range)

@main.route('/book/<int:book_id>')
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    form = ReviewForm()
    
    # Check if book is in user's wishlist
    in_wishlist = False
    if current_user.is_authenticated:
        in_wishlist = Wishlist.query.filter_by(
            user_id=current_user.id,
            book_id=book_id
        ).first() is not None
    
    # Get similar books
    similar_books = book.get_similar_books()
    
    # Get frequently bought together books
    bought_together = book.get_frequently_bought_together()
    
    return render_template('books/detail.html',
                         book=book,
                         similar_books=similar_books,
                         bought_together=bought_together,
                         in_wishlist=in_wishlist,
                         form=form)

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
            # Check if user has purchased the book
            has_purchased = Order.query\
                .join(Order.items)\
                .filter(
                    Order.user_id == current_user.id,
                    Order.items.any(book_id=book_id)
                ).first() is not None
            
            review = Review(
                user_id=current_user.id,
                book_id=book_id,
                rating=form.rating.data,
                comment=form.comment.data,
                verified_purchase=has_purchased
            )
            db.session.add(review)
            db.session.commit()
            
            log_user_activity(current_user, 'review_add',
                            f'Added review for book ID {book_id}')
            
            flash('Your review has been added!', 'success')
    return redirect(url_for('main.book_detail', book_id=book_id))

@main.route('/review/<int:review_id>/vote', methods=['POST'])
@login_required
def vote_review(review_id):
    review = Review.query.get_or_404(review_id)
    review.helpful_votes += 1
    db.session.commit()
    return jsonify({'success': True})

@main.route('/wishlist/toggle/<int:book_id>', methods=['POST'])
@login_required
def toggle_wishlist(book_id):
    wishlist_item = Wishlist.query.filter_by(
        user_id=current_user.id,
        book_id=book_id
    ).first()
    
    if wishlist_item:
        db.session.delete(wishlist_item)
        db.session.commit()
        return jsonify({'success': True, 'added': False})
    else:
        wishlist_item = Wishlist(user_id=current_user.id, book_id=book_id)
        db.session.add(wishlist_item)
        db.session.commit()
        return jsonify({'success': True, 'added': True})

@main.route('/reading-lists')
@login_required
def reading_lists():
    user_lists = ReadingList.query.filter_by(user_id=current_user.id).all()
    return render_template('books/reading_lists.html', reading_lists=user_lists)

@main.route('/reading-list/<int:list_id>')
def view_reading_list(list_id):
    reading_list = ReadingList.query.get_or_404(list_id)
    if not reading_list.is_public and \
       (not current_user.is_authenticated or reading_list.user_id != current_user.id):
        flash('This reading list is private.', 'warning')
        return redirect(url_for('main.index'))
    return render_template('books/reading_list.html', reading_list=reading_list)

@main.route('/reading-list/new', methods=['POST'])
@login_required
def create_reading_list():
    name = request.form.get('name')
    description = request.form.get('description')
    is_public = request.form.get('is_public', 'true') == 'true'
    
    if not name:
        return jsonify({'success': False, 'error': 'Name is required'})
    
    reading_list = ReadingList(
        user_id=current_user.id,
        name=name,
        description=description,
        is_public=is_public
    )
    db.session.add(reading_list)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'list_id': reading_list.id,
        'name': reading_list.name
    })

@main.route('/reading-list/<int:list_id>/add/<int:book_id>', methods=['POST'])
@login_required
def add_to_reading_list(list_id, book_id):
    reading_list = ReadingList.query.get_or_404(list_id)
    if reading_list.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    existing_item = ReadingListItem.query.filter_by(
        reading_list_id=list_id,
        book_id=book_id
    ).first()
    
    if existing_item:
        return jsonify({'success': False, 'error': 'Book already in list'})
    
    item = ReadingListItem(
        reading_list_id=list_id,
        book_id=book_id,
        notes=request.form.get('notes', '')
    )
    db.session.add(item)
    db.session.commit()
    
    return jsonify({'success': True})

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