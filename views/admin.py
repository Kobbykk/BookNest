from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import User, Book, Order, Category, Review, UserActivity
from forms import UserForm
from app import db
from utils.activity_logger import log_user_activity
from werkzeug.security import generate_password_hash
from functools import wraps

admin = Blueprint('admin', __name__, url_prefix='/admin')

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.can(permission):
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@admin.route('/manage_users')
@permission_required('manage_users')
def manage_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin.route('/add_user', methods=['GET', 'POST'])
@permission_required('manage_users')
def add_user():
    form = UserForm()
    if form.validate_on_submit():
        try:
            # Check if email already exists
            if User.query.filter(User.email.ilike(form.email.data)).first():
                flash('Email already registered.', 'danger')
                return render_template('admin/user_form.html', form=form)
            
            user = User(
                username=form.username.data,
                email=form.email.data.lower(),
                password_hash=generate_password_hash(form.password.data),
                role=form.role.data,
                is_admin=form.role.data == 'admin'
            )
            db.session.add(user)
            db.session.commit()
            
            log_user_activity(current_user, 'user_create', 
                            f'Created new user {user.email} with role {user.role}')
            
            flash('User added successfully!', 'success')
            return redirect(url_for('admin.manage_users'))
        except Exception as e:
            current_app.logger.error(f'Error adding user: {str(e)}')
            flash('Error adding user.', 'danger')
            db.session.rollback()
    
    return render_template('admin/user_form.html', form=form)

@admin.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@permission_required('manage_users')
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    
    if form.validate_on_submit():
        try:
            # Check if email is being changed and already exists
            if user.email != form.email.data and \
               User.query.filter(User.email.ilike(form.email.data)).first():
                flash('Email already registered.', 'danger')
                return render_template('admin/user_form.html', form=form, user=user)
            
            user.username = form.username.data
            user.email = form.email.data.lower()
            if form.password.data:
                user.password_hash = generate_password_hash(form.password.data)
            user.role = form.role.data
            user.is_admin = form.role.data == 'admin'
            
            db.session.commit()
            
            log_user_activity(current_user, 'user_update', 
                            f'Updated user {user.email} role to {user.role}')
            
            flash('User updated successfully!', 'success')
            return redirect(url_for('admin.manage_users'))
        except Exception as e:
            current_app.logger.error(f'Error updating user: {str(e)}')
            flash('Error updating user.', 'danger')
            db.session.rollback()
    
    return render_template('admin/user_form.html', form=form, user=user)

@admin.route('/delete_user/<int:user_id>', methods=['POST'])
@permission_required('manage_users')
def delete_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            return jsonify({'success': False, 'error': 'Cannot delete your own account'})
        
        db.session.delete(user)
        db.session.commit()
        
        log_user_activity(current_user, 'user_delete', f'Deleted user {user.email}')
        
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f'Error deleting user: {str(e)}')
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# ... rest of the admin routes ...
