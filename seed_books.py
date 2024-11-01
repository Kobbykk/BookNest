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
                db.create_all()
                print("Created missing tables")

            # Create categories
            categories = [
                Category(name='Programming',
                         description='Programming languages and software development'),
                Category(name='Data Science',
                         description='Data analysis, statistics, and machine learning'),
                Category(name='Web Development',
                         description='Web technologies, frameworks, and best practices'),
                Category(name='Database',
                         description='Database design, administration, and optimization'),
                Category(name='AI',
                         description='Artificial intelligence and deep learning'),
                Category(name='Computer Science',
                         description='Computer science fundamentals and theory'),
                Category(name='Software Engineering',
                         description='Software engineering practices and methodologies')
            ]

            existing_categories = {cat.name for cat in Category.query.all()}
            for category in categories:
                if category.name not in existing_categories:
                    db.session.add(category)

            db.session.commit()
            print("Categories seeded successfully")

            # Real books from Amazon
            books = [{
                'title': 'Design Patterns: Elements of Reusable Object-Oriented Software',
                'author': 'Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides',
                'price': 54.99,
                'description': 'Capturing a wealth of experience about the design of object-oriented software, four top-notch designers present a catalog of simple and succinct solutions to commonly occurring design problems. Previously undocumented, these 23 patterns allow designers to create more flexible, elegant, and ultimately reusable designs without having to rediscover the design solutions themselves.',
                'image_url': 'https://m.media-amazon.com/images/P/0201633612.01._SCLZZZZZZZ_SX500_.jpg',
                'stock': 45,
                'category': 'Programming',
                'isbn': '9780201633610',
                'publisher': 'Addison-Wesley Professional',
                'publication_date': datetime(1994, 11, 10),
                'page_count': 416,
                'language': 'English',
                'tags': 'design patterns,object-oriented,software design',
                'is_featured': True
            }, {
                'title': 'Clean Architecture: A Craftsman\'s Guide to Software Structure and Design',
                'author': 'Robert C. Martin',
                'price': 44.99,
                'description': 'Building upon the success of best-sellers "Clean Code" and "The Clean Coder," legendary software craftsman Robert C. Martin shows how to create software that survives time and change. Martin has teamed up with his son, Micah Martin, to bring to light their best-kept secrets.',
                'image_url': 'https://m.media-amazon.com/images/P/0134494164.01._SCLZZZZZZZ_SX500_.jpg',
                'stock': 60,
                'category': 'Software Engineering',
                'isbn': '9780134494166',
                'publisher': 'Pearson',
                'publication_date': datetime(2017, 9, 17),
                'page_count': 432,
                'language': 'English',
                'tags': 'software architecture,clean code,design principles',
                'is_featured': True
            }, {
                'title': 'Introduction to Algorithms',
                'author': 'Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, Clifford Stein',
                'price': 89.99,
                'description': 'Some books on algorithms are rigorous but incomplete; others cover masses of material but lack rigor. Introduction to Algorithms uniquely combines rigor and comprehensiveness. The book covers a broad range of algorithms in depth, yet makes their design and analysis accessible to all levels of readers.',
                'image_url': 'https://m.media-amazon.com/images/P/026204630X.01._SCLZZZZZZZ_SX500_.jpg',
                'stock': 40,
                'category': 'Computer Science',
                'isbn': '9780262046305',
                'publisher': 'MIT Press',
                'publication_date': datetime(2022, 4, 5),
                'page_count': 1312,
                'language': 'English',
                'tags': 'algorithms,computer science,data structures',
                'is_featured': False
            }, {
                'title': 'Designing Data-Intensive Applications',
                'author': 'Martin Kleppmann',
                'price': 55.99,
                'description': 'Data is at the center of many challenges in system design today. Difficult issues need to be figured out, such as scalability, consistency, reliability, efficiency, and maintainability. In addition, we have an overwhelming variety of tools, including relational databases, NoSQL datastores, stream or batch processors, and message brokers.',
                'image_url': 'https://m.media-amazon.com/images/P/1449373321.01._SCLZZZZZZZ_SX500_.jpg',
                'stock': 55,
                'category': 'Database',
                'isbn': '9781449373320',
                'publisher': "O'Reilly Media",
                'publication_date': datetime(2017, 3, 16),
                'page_count': 616,
                'language': 'English',
                'tags': 'distributed systems,databases,system design',
                'is_featured': True
            }, {
                'title': 'Deep Learning with Python',
                'author': 'François Chollet',
                'price': 59.99,
                'description': 'Written by Keras creator and Google AI researcher François Chollet, this book builds your understanding through intuitive explanations and practical examples. You\'ll explore challenging concepts and practice with applications in computer vision, natural-language processing, and generative models.',
                'image_url': 'https://m.media-amazon.com/images/P/1617296864.01._SCLZZZZZZZ_SX500_.jpg',
                'stock': 50,
                'category': 'AI',
                'isbn': '9781617296864',
                'publisher': 'Manning',
                'publication_date': datetime(2021, 10, 29),
                'page_count': 504,
                'language': 'English',
                'tags': 'deep learning,keras,tensorflow,machine learning',
                'is_featured': True
            }, {
                'title': 'Learning React, 2nd Edition',
                'author': 'Alex Banks, Eve Porcello',
                'price': 49.99,
                'description': 'If you want to learn how to build efficient React applications, this is your book. Ideal for web developers and software engineers who understand how JavaScript, CSS, and HTML work in the browser, this updated edition provides best practices and patterns for writing modern React code.',
                'image_url': 'https://m.media-amazon.com/images/P/1492051721.01._SCLZZZZZZZ_SX500_.jpg',
                'stock': 65,
                'category': 'Web Development',
                'isbn': '9781492051725',
                'publisher': "O'Reilly Media",
                'publication_date': datetime(2020, 6, 23),
                'page_count': 310,
                'language': 'English',
                'tags': 'react,javascript,web development',
                'is_featured': True
            }, {
                'title': 'Python for Data Analysis: Data Wrangling with pandas, NumPy, and Jupyter',
                'author': 'Wes McKinney',
                'price': 49.99,
                'description': 'Get complete instructions for manipulating, processing, cleaning, and crunching datasets in Python. Updated for Python 3.9 and pandas 1.4, this third edition shows you how to solve a broad set of data analysis problems effectively.',
                'image_url': 'https://m.media-amazon.com/images/P/109810403X.01._SCLZZZZZZZ_SX500_.jpg',
                'stock': 70,
                'category': 'Data Science',
                'isbn': '9781098104030',
                'publisher': "O'Reilly Media",
                'publication_date': datetime(2022, 10, 4),
                'page_count': 550,
                'language': 'English',
                'tags': 'python,data analysis,pandas,numpy',
                'is_featured': True
            }, {
                'title': 'Database Internals: A Deep Dive into How Distributed Data Systems Work',
                'author': 'Alex Petrov',
                'price': 64.99,
                'description': 'When it comes to choosing, using, and maintaining a database, understanding its internals is essential. This book explains how databases work from the ground up, providing hard-earned practical knowledge that usually comes from years of experience.',
                'image_url': 'https://m.media-amazon.com/images/P/1492040347.01._SCLZZZZZZZ_SX500_.jpg',
                'stock': 45,
                'category': 'Database',
                'isbn': '9781492040347',
                'publisher': "O'Reilly Media",
                'publication_date': datetime(2019, 10, 1),
                'page_count': 376,
                'language': 'English',
                'tags': 'databases,distributed systems,internals',
                'is_featured': False
            }, {
                'title': 'Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow',
                'author': 'Aurélien Géron',
                'price': 67.99,
                'description': 'Through a series of recent breakthroughs, deep learning has boosted the entire field of machine learning. Now, even programmers who know close to nothing about this technology can use simple, efficient tools to implement programs capable of learning from data.',
                'image_url': 'https://m.media-amazon.com/images/P/1098125975.01._SCLZZZZZZZ_SX500_.jpg',
                'stock': 55,
                'category': 'AI',
                'isbn': '9781098125974',
                'publisher': "O'Reilly Media",
                'publication_date': datetime(2022, 10, 4),
                'page_count': 814,
                'language': 'English',
                'tags': 'machine learning,deep learning,scikit-learn,tensorflow',
                'is_featured': True
            }, {
                'title': 'Fundamentals of Software Architecture',
                'author': 'Mark Richards, Neal Ford',
                'price': 54.99,
                'description': 'Salary surveys worldwide regularly place software architect in the top 10 best jobs, yet no real guide exists to help developers become architects. Until now. This book provides the first comprehensive overview of software architecture\'s many aspects.',
                'image_url': 'https://m.media-amazon.com/images/P/1492043451.01._SCLZZZZZZZ_SX500_.jpg',
                'stock': 50,
                'category': 'Software Engineering',
                'isbn': '9781492043454',
                'publisher': "O'Reilly Media",
                'publication_date': datetime(2020, 2, 4),
                'page_count': 432,
                'language': 'English',
                'tags': 'software architecture,system design,engineering',
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
