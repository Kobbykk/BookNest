import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import inspect
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
        
        try:
            # Import models and create tables in correct order
            from models import (
                User, Category, Book, Order, OrderItem, 
                Review, CartItem, UserActivity, Wishlist,
                ReadingList, ReadingListItem
            )
            
            # Create tables in order
            tables_order = [
                User.__table__,
                Category.__table__,
                Book.__table__,
                Order.__table__,
                OrderItem.__table__,
                Review.__table__,
                CartItem.__table__,
                UserActivity.__table__,
                Wishlist.__table__,
                ReadingList.__table__,
                ReadingListItem.__table__
            ]
            
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            # Create tables in specific order if they don't exist
            for table in tables_order:
                if table.name not in existing_tables:
                    table.create(db.engine)
                    logging.info(f"Created table: {table.name}")
            
            logging.info("All database tables created successfully")
            
        except Exception as e:
            logging.error(f"Error creating database tables: {str(e)}")
            raise e
        
        return app

# Create app instance
app = create_app()
