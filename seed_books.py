from app import app, db
from models import Book, Category

def seed_books():
    categories = {
        'Programming': 'Books about software development and programming languages',
        'Data Science': 'Books covering data analysis, machine learning, and statistics',
        'Web Development': 'Books about web technologies and frameworks',
        'Database': 'Books about database design and administration',
        'Artificial Intelligence': 'Books covering AI, machine learning, and deep learning'
    }
    
    books = [
        {
            "title": "Python Mastery",
            "author": "David Wilson",
            "price": 39.99,
            "description": "Master Python programming with practical examples and best practices. Perfect for beginners and intermediate developers.",
            "image_url": "https://images.unsplash.com/photo-1515879218367-8466d910aaa4",
            "stock": 35,
            "category": "Programming"
        },
        {
            "title": "Data Science Fundamentals",
            "author": "Sarah Johnson",
            "price": 44.99,
            "description": "Learn essential concepts of data science, from statistical analysis to machine learning algorithms.",
            "image_url": "https://images.unsplash.com/photo-1518186285589-2f7649de83e0",
            "stock": 28,
            "category": "Data Science"
        },
        {
            "title": "Modern Web Development",
            "author": "Michael Chen",
            "price": 49.99,
            "description": "Comprehensive guide to modern web development using React, Node.js, and other cutting-edge technologies.",
            "image_url": "https://images.unsplash.com/photo-1593720213428-28a5b9e94613",
            "stock": 42,
            "category": "Web Development"
        },
        {
            "title": "Database Design Patterns",
            "author": "Emily Brown",
            "price": 54.99,
            "description": "Learn advanced database design patterns and optimization techniques for scalable applications.",
            "image_url": "https://images.unsplash.com/photo-1544383835-bda2bc66a55d",
            "stock": 25,
            "category": "Database"
        },
        {
            "title": "AI for Business",
            "author": "Robert Zhang",
            "price": 59.99,
            "description": "Practical guide to implementing AI solutions in business contexts, with real-world case studies.",
            "image_url": "https://images.unsplash.com/photo-1515378791036-0648a3ef77b2",
            "stock": 30,
            "category": "Artificial Intelligence"
        },
        {
            "title": "JavaScript Deep Dive",
            "author": "Lisa Anderson",
            "price": 45.99,
            "description": "In-depth exploration of JavaScript concepts, patterns, and modern features.",
            "image_url": "https://images.unsplash.com/photo-1579468118864-1b9ea3c0db4a",
            "stock": 38,
            "category": "Programming"
        },
        {
            "title": "Machine Learning Applications",
            "author": "James Wilson",
            "price": 64.99,
            "description": "Practical applications of machine learning algorithms with Python and scikit-learn.",
            "image_url": "https://images.unsplash.com/photo-1527474305487-b87b222841cc",
            "stock": 22,
            "category": "Data Science"
        }
    ]

    print("Starting database seeding...")
    
    # Create categories
    for name, description in categories.items():
        if not Category.query.filter_by(name=name).first():
            category = Category(
                name=name,
                description=description,
                display_order=list(categories.keys()).index(name) + 1
            )
            db.session.add(category)
    db.session.commit()
    print("Categories created successfully")

    # Clear existing books
    Book.query.delete()
    db.session.commit()
    print("Existing books cleared")
    
    # Add new books
    for book_data in books:
        book = Book(**book_data)
        db.session.add(book)
    
    db.session.commit()
    print("New books added successfully")
    print(f"Added {len(books)} books across {len(categories)} categories")

if __name__ == "__main__":
    with app.app_context():
        seed_books()
