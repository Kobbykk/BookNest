from app import app, db
from models import Book, Category, CartItem, OrderItem, Review
from datetime import datetime
from sqlalchemy import inspect, text


def seed_books():
    print("Seeding books...")
    with app.app_context():
        try:
            # Verify tables exist before seeding
            inspector = inspect(db.engine)
            if 'categories' not in inspector.get_table_names():
                # Create all tables if they don't exist
                db.create_all()
                print("Created missing tables")

            # Create categories
            categories = [
                Category(name='Programming',
                         description=
                         'Books about programming and software development'),
                Category(
                    name='Data Science',
                    description='Books about data analysis and machine learning'
                ),
                Category(
                    name='Web Development',
                    description='Books about web technologies and frameworks'),
                Category(
                    name='Database',
                    description='Books about database design and administration'
                ),
                Category(
                    name='AI',
                    description=
                    'Books about artificial intelligence and deep learning')
            ]

            # Check for existing categories to avoid duplicates
            existing_categories = {cat.name for cat in Category.query.all()}
            for category in categories:
                if category.name not in existing_categories:
                    db.session.add(category)

            db.session.commit()
            print("Categories seeded successfully")

            # Create sample books
            books = [{
                'title': 'Python Programming',
                'author': 'John Smith',
                'price': 49.99,
                'description':
                'Comprehensive guide to Python programming language',
                'image_url': 'https://picsum.photos/200/300',
                'stock': 100,
                'category': 'Programming',
                'isbn': '9781234567890',
                'publisher': 'Tech Books Inc',
                'publication_date': datetime(2023, 1, 1),
                'page_count': 450,
                'language': 'English',
                'tags': 'python,programming,coding'
            }, {
                'title': 'Data Science Essentials',
                'author': 'Emily Johnson',
                'price': 59.99,
                'description':
                'Essential concepts and techniques in data science',
                'image_url': 'https://picsum.photos/201/300',
                'stock': 75,
                'category': 'Data Science',
                'isbn': '9789876543210',
                'publisher': 'Data Press',
                'publication_date': datetime(2023, 2, 15),
                'page_count': 380,
                'language': 'English',
                'tags': 'data science,analytics,statistics'
            }, {
                'title': 'Web Development with Flask',
                'author': 'Sarah Wilson',
                'price': 45.99,
                'description':
                'Complete guide to building web applications with Flask',
                'image_url': 'https://picsum.photos/200/300',
                'stock': 50,
                'category': 'Web Development',
                'isbn': '9780123456789',
                'publisher': 'Tech Press',
                'publication_date': datetime(2023, 3, 15),
                'page_count': 400,
                'language': 'English',
                'tags': 'flask,python,web development'
            }, {
                'title': 'Machine Learning Basics',
                'author': 'David Chen',
                'price': 55.99,
                'description':
                'Introduction to machine learning concepts and algorithms',
                'image_url': 'https://picsum.photos/200/301',
                'stock': 60,
                'category': 'AI',
                'isbn': '9781234567891',
                'publisher': 'AI Publications',
                'publication_date': datetime(2023, 4, 1),
                'page_count': 350,
                'language': 'English',
                'tags': 'machine learning,AI,python'
            }, {
                'title': 'Database Design Fundamentals',
                'author': 'Michael Rodriguez',
                'price': 52.99,
                'description':
                'Comprehensive guide to database architecture and design patterns',
                'image_url': 'https://picsum.photos/202/300',
                'stock': 85,
                'category': 'Database',
                'isbn': '9781234567892',
                'publisher': 'Database Press',
                'publication_date': datetime(2023, 5, 10),
                'page_count': 420,
                'language': 'English',
                'tags': 'database,SQL,design'
            }, {
                'title': 'Deep Learning with PyTorch',
                'author': 'Lisa Zhang',
                'price': 64.99,
                'description':
                'Advanced deep learning techniques using PyTorch framework',
                'image_url': 'https://picsum.photos/203/300',
                'stock': 45,
                'category': 'AI',
                'isbn': '9781234567893',
                'publisher': 'AI Press',
                'publication_date': datetime(2023, 6, 15),
                'page_count': 480,
                'language': 'English',
                'tags': 'deep learning,pytorch,AI'
            }, {
                'title': 'Modern JavaScript Development',
                'author': 'Alex Thompson',
                'price': 47.99,
                'description':
                'Latest JavaScript features and modern development practices',
                'image_url': 'https://picsum.photos/204/300',
                'stock': 70,
                'category': 'Web Development',
                'isbn': '9781234567894',
                'publisher': 'Web Tech Books',
                'publication_date': datetime(2023, 7, 1),
                'page_count': 380,
                'language': 'English',
                'tags': 'javascript,es6,web development'
            }, {
                'title': 'Big Data Analytics',
                'author': 'Robert Kumar',
                'price': 69.99,
                'description':
                'Processing and analyzing large-scale data sets',
                'image_url': 'https://picsum.photos/205/300',
                'stock': 55,
                'category': 'Data Science',
                'isbn': '9781234567895',
                'publisher': 'Data Science Press',
                'publication_date': datetime(2023, 8, 20),
                'page_count': 520,
                'language': 'English',
                'tags': 'big data,hadoop,spark'
            }, {
                'title': 'Clean Code in Python',
                'author': 'Maria Garcia',
                'price': 51.99,
                'description':
                'Writing maintainable and efficient Python code',
                'image_url': 'https://picsum.photos/206/300',
                'stock': 90,
                'category': 'Programming',
                'isbn': '9781234567896',
                'publisher': 'Code Masters',
                'publication_date': datetime(2023, 9, 5),
                'page_count': 340,
                'language': 'English',
                'tags': 'python,clean code,best practices'
            }]

            # Check for existing books to avoid duplicates
            existing_isbns = {book.isbn for book in Book.query.all()}
            for book_data in books:
                if book_data['isbn'] not in existing_isbns:
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
