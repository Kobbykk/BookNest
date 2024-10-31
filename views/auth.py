from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from models import User
from forms import LoginForm, RegisterForm
from app import db
from utils.activity_logger import log_user_activity

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # Normalize email to lowercase for case-insensitive comparison
        email = form.email.data.lower()
        current_app.logger.info(f"Login attempt for email: {email}")
        
        user = User.query.filter(User.email.ilike(email)).first()
        if user:
            current_app.logger.info(f"User found with ID: {user.id}")
            if check_password_hash(user.password_hash, form.password.data):
                current_app.logger.info(f"Password verification successful for user {user.id}")
                login_user(user)
                log_user_activity(user, 'login', 'User logged in successfully')
                flash('Login successful!', 'success')
                return redirect(url_for('main.index'))
            else:
                current_app.logger.warning(f"Password verification failed for user {user.id}")
        else:
            current_app.logger.warning(f"No user found with email: {email}")
        
        flash('Invalid email or password', 'danger')
    return render_template('auth/login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # Normalize email to lowercase before saving
        email = form.email.data.lower()
        if User.query.filter(User.email.ilike(email)).first():
            flash('Email already registered', 'danger')
            return render_template('auth/register.html', form=form)

        user = User(
            username=form.username.data,
            email=email,
            password_hash=generate_password_hash(form.password.data)
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Registration successful!', 'success')
        return redirect(url_for('main.index'))
    return render_template('auth/register.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))
