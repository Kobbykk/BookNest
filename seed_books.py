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
                    'image_url': 'https://placekitten.com/200/300',
                    'stock': 100,
                    'category': 'Programming',
                    'isbn': '9781234567890',
                    'publisher': 'Tech Books Inc',
                    'publication_date': datetime(2023, 1, 1),
                    'page_count': 450,
                    'language': 'English',
                    'tags': 'python,programming,coding',
                    'preview_content': '''
                    Chapter 1: Introduction to Python
                    
                    Python is a high-level, interpreted programming language that emphasizes code readability with the use of significant indentation. Python's simple, easy-to-learn syntax emphasizes readability and therefore reduces the cost of program maintenance.
                    
                    Key Features:
                    - Easy to learn and read
                    - Extensive standard library
                    - Dynamic typing
                    - Memory management
                    - Object-oriented programming
                    
                    Let's start with a simple example:
                    
                    ```python
                    print("Hello, World!")
                    ```
                    '''
                },
                {
                    'title': 'Data Science Essentials',
                    'author': 'Emily Johnson',
                    'price': 59.99,
                    'description': 'Essential concepts and techniques in data science',
                    'image_url': 'https://placekitten.com/201/300',
                    'stock': 75,
                    'category': 'Data Science',
                    'isbn': '9789876543210',
                    'publisher': 'Data Press',
                    'publication_date': datetime(2023, 2, 15),
                    'page_count': 380,
                    'language': 'English',
                    'tags': 'data science,analytics,statistics',
                    'preview_content': '''
                    Chapter 1: Introduction to Data Science
                    
                    Data Science combines multiple fields, including statistics, scientific methods, and data analysis, to extract value from data.
                    
                    Key Concepts:
                    - Data Collection
                    - Data Cleaning
                    - Exploratory Data Analysis
                    - Statistical Analysis
                    - Machine Learning
                    
                    Example of data analysis using Python:
                    
                    ```python
                    import pandas as pd
                    
                    # Load and analyze data
                    data = pd.read_csv('dataset.csv')
                    print(data.describe())
                    ```
                    '''
                },
                # Add more sample books...
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
