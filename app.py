import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import generate_password_hash
import logging

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
mail = Mail()

# create the app
app = Flask(__name__)
# Configure logging
app.logger.setLevel(logging.INFO)

# setup a secret key, required by sessions
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
# configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

# initialize the extensions
db.init_app(app)
login_manager.init_app(app)
mail.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

with app.app_context():
    # Make sure to import the models here
    from models import User, Book, Order, OrderItem, Category, Review, Discount, BookDiscount
    
    # Create tables if they don't exist
    db.create_all()

    # Create admin user if not exists
    admin_email = 'admin@gmail.com'
    admin = User.query.filter(User.email.ilike(admin_email)).first()
    if not admin:
        app.logger.info("Creating new admin user")
        admin = User(
            username='admin',
            email=admin_email.lower(),
            password_hash=generate_password_hash('Password123'),
            is_admin=True
        )
        try:
            db.session.add(admin)
            db.session.commit()
            app.logger.info("Admin user created successfully")
        except Exception as e:
            app.logger.error(f"Error creating admin user: {str(e)}")
            db.session.rollback()
    else:
        app.logger.info("Admin user already exists")

    # Register blueprints
    from views.auth import auth
    from views.main import main
    from views.admin import admin as admin_blueprint
    from views.cart import cart
    
    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(admin_blueprint)
    app.register_blueprint(cart)
