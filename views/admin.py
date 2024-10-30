from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import Book, Order, OrderItem, User, Category, Discount, BookDiscount
from forms import BookForm, CategoryForm, DiscountForm
from app import db
from utils.email import send_order_status_email
from datetime import datetime

admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.route('/')
@login_required
def dashboard():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))
    books = Book.query.all()
    orders = Order.query.all()
    users = User.query.all()
    categories = [cat[0] for cat in db.session.query(Category.name).distinct()]
    discounts = Discount.query.all()
    
    return render_template('admin/dashboard.html', 
                         books=books, 
                         orders=orders,
                         users=users,
                         categories=categories,
                         discounts=discounts)

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

# Rest of the existing routes...
