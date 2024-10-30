from app import app, db
from models import Book, Category

def seed_books():
    # First ensure categories exist
    categories = ['Programming', 'Data Science', 'Web Development', 'Database']
    for cat_name in categories:
        if not Category.query.filter_by(name=cat_name).first():
            category = Category(
                name=cat_name,
                display_order=categories.index(cat_name) + 1
            )
            db.session.add(category)
    db.session.commit()
    
    # Sample books with realistic data and categories
    books = [
        {
            "title": "The Art of Programming",
            "author": "Robert C. Martin",
            "price": 49.99,
            "description": "A comprehensive guide to software craftsmanship, covering best practices, design patterns, and coding principles that help developers write better code.",
            "image_url": "https://images.unsplash.com/photo-1532012197267-da84d127e765",
            "stock": 25,
            "category": "Programming"
        },
        {
            "title": "Data Science Fundamentals",
            "author": "Sarah Johnson",
            "price": 39.99,
            "description": "Learn the essential concepts of data science, from statistical analysis to machine learning, with practical examples and real-world applications.",
            "image_url": "https://images.unsplash.com/photo-1543002588-bfa74002ed7e",
            "stock": 30,
            "category": "Data Science"
        },
        {
            "title": "Web Development Mastery",
            "author": "Michael Chen",
            "price": 45.99,
            "description": "Master modern web development technologies and frameworks. Covers everything from HTML5 and CSS3 to React and Node.js.",
            "image_url": "https://images.unsplash.com/photo-1532012197267-da84d127e765",
            "stock": 20,
            "category": "Web Development"
        },
        {
            "title": "Python for Beginners",
            "author": "David Wilson",
            "price": 29.99,
            "description": "Start your programming journey with Python. This book covers all the basics you need to know to become proficient in Python programming.",
            "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c",
            "stock": 40,
            "category": "Programming"
        },
        {
            "title": "Database Design Patterns",
            "author": "Emily Brown",
            "price": 54.99,
            "description": "Learn advanced database design patterns and optimization techniques. Perfect for database administrators and software architects.",
            "image_url": "https://images.unsplash.com/photo-1532012197267-da84d127e765",
            "stock": 15,
            "category": "Database"
        }
    ]

    with app.app_context():
        # Clear existing books
        Book.query.delete()
        
        # Add new books
        for book_data in books:
            book = Book(**book_data)
            db.session.add(book)
        
        # Commit the changes
        db.session.commit()
        print("Sample books and categories have been added to the database.")

if __name__ == "__main__":
    seed_books()
