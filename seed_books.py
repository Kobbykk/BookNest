from app import app, db
from models import Book, Category, CartItem, OrderItem, Review
from datetime import datetime
import random

def seed_books():
    print("Seeding books...")
    with app.app_context():
        try:
            # Create categories
            categories = [
                Category(name='Programming', description='Books about programming and software development'),
                Category(name='Data Science', description='Books about data analysis and machine learning'),
                Category(name='Web Development', description='Books about web technologies and frameworks'),
                Category(name='Database', description='Books about database design and administration'),
                Category(name='AI', description='Books about artificial intelligence and deep learning')
            ]
            
            for category in categories:
                db.session.add(category)
            db.session.commit()
            
            # Create sample books
            books = [
                {
                    'title': 'Python Programming',
                    'author': 'John Smith',
                    'price': 49.99,
                    'description': 'Comprehensive guide to Python programming language',
                    'image_url': 'https://picsum.photos/200/300',
                    'stock': 100,
                    'category': 'Programming',
                    'isbn': '9781234567890',
                    'publisher': 'Tech Books Inc',
                    'publication_date': datetime(2023, 1, 1),
                    'page_count': 450,
                    'language': 'English',
                    'tags': 'python,programming,coding'
                },
                {
                    'title': 'Data Science Essentials',
                    'author': 'Emily Johnson',
                    'price': 59.99,
                    'description': 'Essential concepts and techniques in data science',
                    'image_url': 'https://picsum.photos/201/300',
                    'stock': 75,
                    'category': 'Data Science',
                    'isbn': '9789876543210',
                    'publisher': 'Data Press',
                    'publication_date': datetime(2023, 2, 15),
                    'page_count': 380,
                    'language': 'English',
                    'tags': 'data science,analytics,statistics'
                },
                {
                    'title': 'Web Development with Flask',
                    'author': 'Sarah Wilson',
                    'price': 45.99,
                    'description': 'Complete guide to building web applications with Flask',
                    'image_url': 'https://picsum.photos/200/300',
                    'stock': 50,
                    'category': 'Web Development',
                    'isbn': '9780123456789',
                    'publisher': 'Tech Press',
                    'publication_date': datetime(2023, 3, 15),
                    'page_count': 400,
                    'language': 'English',
                    'tags': 'flask,python,web development'
                },
                {
                    'title': 'Machine Learning Basics',
                    'author': 'David Chen',
                    'price': 55.99,
                    'description': 'Introduction to machine learning concepts and algorithms',
                    'image_url': 'https://picsum.photos/200/301',
                    'stock': 60,
                    'category': 'AI',
                    'isbn': '9781234567891',
                    'publisher': 'AI Publications',
                    'publication_date': datetime(2023, 4, 1),
                    'page_count': 350,
                    'language': 'English',
                    'tags': 'machine learning,AI,python'
                }
            ]
            
            for book_data in books:
                book = Book(**book_data)
                db.session.add(book)
            
            db.session.commit()
            print("Books seeded successfully")
            
        except Exception as e:
            print(f"Error seeding books: {str(e)}")
            db.session.rollback()
            raise e

if __name__ == "__main__":
    seed_books()
