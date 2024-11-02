from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User, UserActivity
from forms import LoginForm, RegisterForm
from utils.activity_logger import log_user_activity

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(User.email.ilike(form.email.data)).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            log_user_activity(user, 'user_login', 'User logged in')
            flash('Logged in successfully!', 'success')
            
            # Redirect to the page they were trying to access, or home page
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):  # Ensure the URL is relative
                return redirect(next_page)
            return redirect(url_for('main.index'))
        flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    log_user_activity(current_user, 'user_logout', 'User logged out')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter(User.email.ilike(form.email.data)).first():
            flash('Email already registered.', 'danger')
            return render_template('auth/register.html', form=form)
        
        user = User(
            username=form.username.data,
            email=form.email.data.lower(),
            password_hash=generate_password_hash(form.password.data)
        )
        db.session.add(user)
        db.session.commit()
        
        log_user_activity(user, 'user_register', 'User registered')
        login_user(user)
        flash('Registration successful!', 'success')
        return redirect(url_for('main.index'))
    return render_template('auth/register.html', form=form)
