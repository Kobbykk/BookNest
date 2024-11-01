from app import app, db
from models import Book, Category, CartItem, OrderItem, Review, BookFormat
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
                'tags': 'python,programming,coding',
                'is_featured': True
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
                'tags': 'data science,analytics,statistics',
                'is_featured': True
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
                'tags': 'flask,python,web development',
                'is_featured': True
            }]

            # Check for existing books to avoid duplicates
            existing_isbns = {book.isbn for book in Book.query.all()}
            for book_data in books:
                if book_data['isbn'] not in existing_isbns:
                    book = Book(**book_data)
                    
                    # Add formats for each book
                    formats = [
                        BookFormat(
                            format_type='hardcover',
                            price=book_data['price'] + 10,
                            stock=50,
                            isbn=f"{book_data['isbn']}-H"
                        ),
                        BookFormat(
                            format_type='paperback',
                            price=book_data['price'],
                            stock=100,
                            isbn=f"{book_data['isbn']}-P"
                        ),
                        BookFormat(
                            format_type='ebook',
                            price=book_data['price'] - 10,
                            stock=999,
                            isbn=f"{book_data['isbn']}-E"
                        )
                    ]
                    book.formats.extend(formats)
                    db.session.add(book)

            db.session.commit()
            print("Books seeded successfully")

        except Exception as e:
            print(f"Error seeding books: {str(e)}")
            db.session.rollback()
            raise e


if __name__ == "__main__":
    seed_books()
