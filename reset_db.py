from app import app, db
from sqlalchemy import text, inspect
import logging

def reset_database():
    print("Resetting database...")
    with app.app_context():
        try:
            # Drop all tables in correct order
            db.session.execute(text("""
                DROP TABLE IF EXISTS reading_list_items CASCADE;
                DROP TABLE IF EXISTS reading_lists CASCADE;
                DROP TABLE IF EXISTS wishlists CASCADE;
                DROP TABLE IF EXISTS user_activities CASCADE;
                DROP TABLE IF EXISTS cart_items CASCADE;
                DROP TABLE IF EXISTS reviews CASCADE;
                DROP TABLE IF EXISTS order_items CASCADE;
                DROP TABLE IF EXISTS orders CASCADE;
                DROP TABLE IF EXISTS books CASCADE;
                DROP TABLE IF EXISTS categories CASCADE;
                DROP TABLE IF EXISTS users CASCADE;
            """))
            db.session.commit()
            print("All tables dropped")
            
            # Create tables in order
            from models import User, Category, Book, Order, OrderItem, Review, CartItem, UserActivity, Wishlist, ReadingList, ReadingListItem
            
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
            
            # Create tables in specific order
            for table in tables_order:
                if table.name not in existing_tables:
                    table.create(db.engine)
                    print(f"Created table: {table.name}")
            
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
