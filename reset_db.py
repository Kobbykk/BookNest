from app import app, db
from sqlalchemy import text, inspect
import logging
import os

def reset_database():
    print("Resetting database...")
    with app.app_context():
        try:
            # Drop schema and recreate
            db.session.execute(text('DROP SCHEMA public CASCADE'))
            db.session.execute(text('CREATE SCHEMA public'))
            db.session.execute(text(f'GRANT ALL ON SCHEMA public TO {os.environ.get("PGUSER")}'))
            db.session.execute(text('GRANT ALL ON SCHEMA public TO public'))
            
            db.session.commit()
            print("Schema reset complete")
            
            # Import models
            from models import (
                User, Category, Book, BookFormat, Order, OrderItem, 
                Review, CartItem, UserActivity, Wishlist,
                ReadingList, ReadingListItem
            )
            
            # Create all tables using SQLAlchemy's create_all()
            db.create_all()
            print("All tables created successfully")
            
            # Create admin user
            from werkzeug.security import generate_password_hash
            
            admin = User()
            admin_data = {
                'username': 'admin',
                'email': 'admin@gmail.com',
                'password_hash': generate_password_hash('Password123'),
                'is_admin': True,
                'role': 'admin'
            }
            for key, value in admin_data.items():
                setattr(admin, key, value)
            
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully")
            
            # Create default categories
            default_categories = [
                ('Programming', 'Books about programming languages and software development', 1),
                ('Data Science', 'Books about data analysis and machine learning', 2),
                ('Web Development', 'Books about web technologies and frameworks', 3),
                ('Database', 'Books about database systems and management', 4),
                ('AI', 'Books about artificial intelligence and machine learning', 5),
                ('Computer Science', 'Books about computer science fundamentals', 6),
                ('Software Engineering', 'Books about software engineering practices', 7)
            ]
            
            for name, desc, order in default_categories:
                category = Category()
                category.name = name
                category.description = desc
                category.display_order = order
                db.session.add(category)
            
            db.session.commit()
            print("Default categories created successfully")
            print("Database reset complete")
            
        except Exception as e:
            print(f"Error resetting database: {str(e)}")
            db.session.rollback()
            raise e

if __name__ == "__main__":
    reset_database()