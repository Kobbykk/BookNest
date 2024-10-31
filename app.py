import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from sqlalchemy.orm import DeclarativeBase
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

class Base(DeclarativeBase):
    pass

# Initialize extensions without app
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
mail = Mail()

def create_app():
    app = Flask(__name__)
    
    # Configure app
    app.config.update(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "a secret key"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL"),
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_recycle": 300,
            "pool_pre_ping": True,
        },
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
        MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
        MAIL_DEFAULT_SENDER=os.environ.get('MAIL_USERNAME')
    )
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    with app.app_context():
        from views.auth import auth
        from views.main import main
        from views.admin import admin
        from views.cart import cart
        
        app.register_blueprint(auth)
        app.register_blueprint(main)
        app.register_blueprint(admin)
        app.register_blueprint(cart)
        
        # Initialize database
        from models import User, Book, Order, OrderItem, Category, Review, CartItem, UserActivity
        db.create_all()
        
        return app

# Create app instance
app = create_app()
