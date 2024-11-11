from app import app, db
from sqlalchemy import text, inspect
import logging

def reset_database():
    print("Resetting database...")
    with app.app_context():
        try:
            # Drop schema and recreate
            db.session.execute(text('DROP SCHEMA public CASCADE'))
            db.session.execute(text('CREATE SCHEMA public'))
            db.session.commit()
            print("Schema reset complete")
            
            # Create tables in correct dependency order
            from models import (
                User, Category, Book, Order, OrderItem, 
                Review, CartItem, UserActivity, Wishlist,
                ReadingList, ReadingListItem, BookFormat
            )
            
            # Create tables in correct order
            db.create_all()
            print("All tables created successfully")
            
            # Create admin user
            from werkzeug.security import generate_password_hash
            
            admin = User(
                username='admin',
                email='admin@gmail.com',
                password_hash=generate_password_hash('Password123'),
                is_admin=True,
                role='admin'
            )
            
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully")
            
            print("Database reset complete")
            
        except Exception as e:
            print(f"Error resetting database: {str(e)}")
            db.session.rollback()
            raise e

if __name__ == "__main__":
    reset_database()
