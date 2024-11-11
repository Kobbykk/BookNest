from app import app, db
from models import Book, BookFormat, Category
from datetime import datetime
from sqlalchemy import inspect

def seed_books():
    print("Seeding books...")
    with app.app_context():
        try:
            # Verify tables exist before seeding
            inspector = inspect(db.engine)
            if 'books' not in inspector.get_table_names():
                print("Tables don't exist, please run reset_db.py first")
                return

            # Real books from Amazon
            books = [{
                'title': 'Design Patterns: Elements of Reusable Object-Oriented Software',
                'author': 'Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides',
                'price': 54.99,
                'description': 'Capturing a wealth of experience about the design of object-oriented software...',
                'image_url': 'https://m.media-amazon.com/images/P/0201633612.01._SCLZZZZZZZ_SX500_.jpg',
                'stock': 45,
                'category_name': 'Programming',
                'isbn': '9780201633610',
                'publisher': 'Addison-Wesley Professional',
                'publication_date': datetime(1994, 11, 10),
                'page_count': 416,
                'language': 'English',
                'tags': 'design patterns,object-oriented,software design',
                'is_featured': True
            }]

            # Check for existing books to avoid duplicates
            existing_isbns = {book.isbn for book in Book.query.all()}
            
            for book_data in books:
                if book_data['isbn'] not in existing_isbns:
                    # Get or create category
                    category = Category.query.filter_by(name=book_data['category_name']).first()
                    if not category:
                        category = Category(
                            name=book_data['category_name'],
                            description=f"Books about {book_data['category_name'].lower()}",
                            display_order=99
                        )
                        db.session.add(category)
                        db.session.flush()
                    
                    book = Book()
                    for key, value in book_data.items():
                        if key != 'category_name':  # Skip category_name as we handle it separately
                            setattr(book, key, value)
                    
                    # Set both category_id and category_name
                    book.category_id = category.id
                    book.category_name = category.name
                    
                    # Add formats for each book
                    formats_data = [
                        {
                            'format_type': 'hardcover',
                            'price': book_data['price'] + 10,
                            'stock': 50,
                            'isbn': f"{book_data['isbn']}-H"
                        },
                        {
                            'format_type': 'paperback',
                            'price': book_data['price'],
                            'stock': 100,
                            'isbn': f"{book_data['isbn']}-P"
                        },
                        {
                            'format_type': 'ebook',
                            'price': book_data['price'] - 10,
                            'stock': 999,
                            'isbn': f"{book_data['isbn']}-E"
                        }
                    ]

                    for format_data in formats_data:
                        book_format = BookFormat()
                        for key, value in format_data.items():
                            setattr(book_format, key, value)
                        book.formats.append(book_format)

                    db.session.add(book)

            db.session.commit()
            print("Books seeded successfully")

        except Exception as e:
            print(f"Error seeding books: {str(e)}")
            db.session.rollback()
            raise e

if __name__ == "__main__":
    seed_books()
