from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import Book, Order, OrderItem, User, Category, Discount, BookDiscount, UserActivity, Review
from forms import BookForm, CategoryForm, DiscountForm
from app import db
from utils.email import send_order_status_email
from datetime import datetime, timedelta
from sqlalchemy import desc

admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.route('/')
@login_required
def dashboard():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))
    books = Book.query.all()
    orders = Order.query.order_by(Order.created_at.desc()).all()
    users = User.query.all()
    categories = [cat[0] for cat in db.session.query(Category.name).distinct()]
    discounts = Discount.query.all()
    
    return render_template('admin/dashboard.html', 
                         books=books, 
                         orders=orders,
                         users=users,
                         categories=categories,
                         discounts=discounts)

@admin.route('/orders/<int:order_id>/status', methods=['POST'])
@login_required
def update_order_status(order_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'})
    
    try:
        order = Order.query.get_or_404(order_id)
        new_status = request.json.get('status')
        
        if new_status not in Order.STATUS_CHOICES:
            return jsonify({'success': False, 'error': 'Invalid status value'})
        
        order.status = new_status
        db.session.commit()
        
        # Send email notification
        send_order_status_email(order.user.email, order.id, new_status, order.items)
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/manage_users')
@login_required
def manage_users():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))
    
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
def toggle_admin(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'})
    
    if current_user.id == user_id:
        return jsonify({'success': False, 'error': 'Cannot modify your own admin status'})
    
    user = User.query.get_or_404(user_id)
    try:
        user.is_admin = not user.is_admin
        db.session.commit()
        return jsonify({
            'success': True,
            'is_admin': user.is_admin
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/users/<int:user_id>/profile')
@login_required
def get_user_profile(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'})
    
    try:
        user = User.query.get_or_404(user_id)
        
        activities = UserActivity.query.filter_by(user_id=user_id)\
            .order_by(UserActivity.timestamp.desc())\
            .limit(5)\
            .all()
        
        orders = Order.query.filter_by(user_id=user_id)\
            .order_by(Order.created_at.desc())\
            .limit(5)\
            .all()
        
        reviews = db.session.query(Review, Book.title)\
            .join(Book)\
            .filter(Review.user_id == user_id)\
            .order_by(Review.created_at.desc())\
            .limit(5)\
            .all()
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'created_at': user.created_at.isoformat(),
                'is_admin': user.is_admin
            },
            'activities': [{
                'activity_type': activity.activity_type,
                'description': activity.description,
                'timestamp': activity.timestamp.isoformat()
            } for activity in activities],
            'orders': [{
                'id': order.id,
                'total': order.total,
                'status': order.status,
                'created_at': order.created_at.isoformat()
            } for order in orders],
            'reviews': [{
                'book_title': book_title,
                'rating': review.rating,
                'comment': review.comment,
                'created_at': review.created_at.isoformat()
            } for review, book_title in reviews]
        })
    except Exception as e:
        current_app.logger.error(f'Error fetching user profile: {str(e)}')
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/book/add', methods=['GET', 'POST'])
@login_required
def add_book():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))
    
    form = BookForm()
    if form.validate_on_submit():
        try:
            book = Book(
                title=form.title.data,
                author=form.author.data,
                price=form.price.data,
                description=form.description.data,
                image_url=form.image_url.data,
                stock=form.stock.data,
                category=form.category_id.data
            )
            db.session.add(book)
            db.session.commit()
            flash('Book added successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            current_app.logger.error(f'Error adding book: {str(e)}')
            flash('Error adding book.', 'danger')
            db.session.rollback()
    
    return render_template('admin/book_form.html', form=form, title='Add Book')

@admin.route('/book/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))
    
    book = Book.query.get_or_404(book_id)
    form = BookForm(obj=book)
    
    if form.validate_on_submit():
        try:
            book.title = form.title.data
            book.author = form.author.data
            book.price = form.price.data
            book.description = form.description.data
            book.image_url = form.image_url.data
            book.stock = form.stock.data
            book.category = form.category_id.data
            db.session.commit()
            flash('Book updated successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            current_app.logger.error(f'Error updating book: {str(e)}')
            flash('Error updating book.', 'danger')
            db.session.rollback()
    
    return render_template('admin/book_form.html', form=form, title='Edit Book')

@admin.route('/manage_categories', methods=['GET', 'POST'])
@login_required
def manage_categories():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))
    
    form = CategoryForm()
    if form.validate_on_submit():
        try:
            category = Category(
                name=form.name.data,
                description=form.description.data
            )
            db.session.add(category)
            db.session.commit()
            flash('Category added successfully.', 'success')
        except Exception as e:
            current_app.logger.error(f'Error adding category: {str(e)}')
            flash('Error adding category.', 'danger')
            db.session.rollback()
    
    categories = Category.query.order_by(Category.id).all()
    return render_template('admin/categories.html', categories=categories, form=form)

@admin.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'})
    
    category = Category.query.get_or_404(category_id)
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'category': {
                'id': category.id,
                'name': category.name,
                'description': category.description
            }
        })
    
    form = CategoryForm()
    if form.validate_on_submit():
        try:
            category.name = form.name.data
            category.description = form.description.data
            db.session.commit()
            flash('Category updated successfully.', 'success')
            return jsonify({'success': True})
        except Exception as e:
            current_app.logger.error(f'Error updating category: {str(e)}')
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({'success': False, 'error': 'Invalid form data'})

@admin.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'})
    
    category = Category.query.get_or_404(category_id)
    if category.books:
        return jsonify({'success': False, 'error': 'Cannot delete category with associated books'})
    
    try:
        db.session.delete(category)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f'Error deleting category: {str(e)}')
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin.route('/user-activities')
@login_required
def user_activities():
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))
    
    user_id = request.args.get('user_id', type=int)
    activity_type = request.args.get('activity_type')
    days = request.args.get('days', type=int, default=7)
    
    query = UserActivity.query
    
    if user_id:
        query = query.filter(UserActivity.user_id == user_id)
    if activity_type:
        query = query.filter(UserActivity.activity_type == activity_type)
    if days:
        since_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(UserActivity.timestamp >= since_date)
    
    page = request.args.get('page', 1, type=int)
    activities = query.order_by(desc(UserActivity.timestamp)).paginate(
        page=page, per_page=20, error_out=False)
    
    activity_types = db.session.query(UserActivity.activity_type).distinct().all()
    activity_types = [t[0] for t in activity_types]
    
    users = User.query.all()
    
    return render_template('admin/user_activities.html',
                         activities=activities,
                         activity_types=activity_types,
                         users=users,
                         selected_user_id=user_id,
                         selected_activity_type=activity_type,
                         selected_days=days)