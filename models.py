from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import func, text
from sqlalchemy.ext.hybrid import hybrid_property
from extensions import db
from werkzeug.security import check_password_hash
from utils.image_optimizer import ImageOptimizer
from collections import Counter
import numpy as np
from sqlalchemy import and_

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(20), default='customer')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='user', lazy=True, cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='user', lazy=True, cascade='all, delete-orphan')
    cart_items = db.relationship('CartItem', backref='user', lazy=True, cascade='all, delete-orphan')
    activities = db.relationship('UserActivity', backref='user', lazy=True, cascade='all, delete-orphan')
    wishlists = db.relationship('Wishlist', backref='user', lazy=True, cascade='all, delete-orphan')
    reading_lists = db.relationship('ReadingList', backref='user', lazy=True, cascade='all, delete-orphan')

    ROLES = ['admin', 'manager', 'editor', 'customer']

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, role):
        return self.role == role or (role == 'admin' and self.is_admin)
    
    def get_permissions(self):
        permissions = {
            'admin': ['manage_users', 'manage_books', 'manage_orders', 'manage_categories'],
            'manager': ['manage_books', 'manage_orders', 'manage_categories'],
            'editor': ['manage_books', 'manage_categories'],
            'customer': []
        }
        return permissions.get(self.role, [])

    def can(self, permission):
        return permission in self.get_permissions() or self.is_admin

    def get_reading_preferences(self):
        """Get user's reading preferences based on ratings, purchases, and reading lists"""
        preferences = {
            'categories': Counter(),
            'tags': Counter(),
            'authors': Counter()
        }
        
        # Add weights from reviews
        for review in self.reviews:
            if review.rating >= 4:  # Consider only positive reviews
                preferences['categories'][review.book.category] += 2
                if review.book.tags:
                    for tag in review.book.tags.split(','):
                        preferences['tags'][tag.strip()] += 2
                preferences['authors'][review.book.author] += 2

        # Add weights from purchases
        for order in self.orders:
            for item in order.items:
                preferences['categories'][item.book.category] += 1
                if item.book.tags:
                    for tag in item.book.tags.split(','):
                        preferences['tags'][tag.strip()] += 1
                preferences['authors'][item.book.author] += 1

        # Add weights from reading lists
        for reading_list in self.reading_lists:
            for item in reading_list.items:
                preferences['categories'][item.book.category] += 0.5
                if item.book.tags:
                    for tag in item.book.tags.split(','):
                        preferences['tags'][tag.strip()] += 0.5
                preferences['authors'][item.book.author] += 0.5

        return preferences

    def get_recommended_books(self, limit=10):
        """Get personalized book recommendations for the user"""
        preferences = self.get_reading_preferences()
        
        # Get books the user has already interacted with
        interacted_books = set()
        for review in self.reviews:
            interacted_books.add(review.book_id)
        for order in self.orders:
            for item in order.items:
                interacted_books.add(item.book_id)

        # Calculate recommendation scores for all other books
        all_books = Book.query.filter(Book.id.notin_(interacted_books)).all()
        book_scores = []

        for book in all_books:
            score = 0
            
            # Category match
            if book.category in preferences['categories']:
                score += preferences['categories'][book.category] * 2
            
            # Tag matches
            if book.tags:
                for tag in book.tags.split(','):
                    tag = tag.strip()
                    if tag in preferences['tags']:
                        score += preferences['tags'][tag]
            
            # Author match
            if book.author in preferences['authors']:
                score += preferences['authors'][book.author] * 1.5
            
            # Rating factor
            score *= (1 + book.average_rating / 5.0)
            
            book_scores.append((book, score))

        # Sort by score and return top recommendations
        book_scores.sort(key=lambda x: x[1], reverse=True)
        return [book for book, _ in book_scores[:limit]]

    def get_similar_users(self, limit=5):
        """Find users with similar reading preferences"""
        user_scores = {}
        
        # Get all users except self
        other_users = User.query.filter(User.id != self.id).all()
        
        my_prefs = self.get_reading_preferences()
        
        for other_user in other_users:
            score = 0
            other_prefs = other_user.get_reading_preferences()
            
            # Compare category preferences
            for category, weight in my_prefs['categories'].items():
                if category in other_prefs['categories']:
                    score += min(weight, other_prefs['categories'][category])
            
            # Compare tag preferences
            for tag, weight in my_prefs['tags'].items():
                if tag in other_prefs['tags']:
                    score += min(weight, other_prefs['tags'][tag])
            
            # Compare author preferences
            for author, weight in my_prefs['authors'].items():
                if author in other_prefs['authors']:
                    score += min(weight, other_prefs['authors'][author])
            
            user_scores[other_user] = score
        
        # Sort by score and return top similar users
        similar_users = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)
        return [user for user, _ in similar_users[:limit]]

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    display_order = db.Column(db.Integer, default=0)
    books = db.relationship('Book', backref='category_ref', lazy=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))

class BookFormat(db.Model):
    __tablename__ = 'book_formats'
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    format_type = db.Column(db.String(20), nullable=False)  # hardcover, paperback, ebook
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    isbn = db.Column(db.String(20))
    book = db.relationship('Book', back_populates='formats')

class Book(db.Model):
    __tablename__ = 'books'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    author = db.Column(db.String(100), nullable=False, index=True)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    stock = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50), db.ForeignKey('categories.name', onupdate='CASCADE', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviews = db.relationship('Review', backref='book', lazy=True, cascade='all, delete-orphan')
    cart_items = db.relationship('CartItem', backref='book', lazy=True, cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', backref='book', lazy=True)
    preview_content = db.Column(db.Text)
    isbn = db.Column(db.String(13), unique=True)
    publisher = db.Column(db.String(100))
    publication_date = db.Column(db.Date)
    page_count = db.Column(db.Integer)
    language = db.Column(db.String(50))
    tags = db.Column(db.String(500))
    wishlisted_by = db.relationship('Wishlist', backref='book', lazy=True, cascade='all, delete-orphan')
    reading_list_items = db.relationship('ReadingListItem', backref='book', lazy=True, cascade='all, delete-orphan')
    formats = db.relationship('BookFormat', back_populates='book', lazy=True, cascade='all, delete-orphan')
    is_featured = db.Column(db.Boolean, default=False)

    @property
    def thumbnail_url(self):
        """Get thumbnail version of book cover"""
        return ImageOptimizer.get_optimized_url(self.image_url, 'thumbnail')
        
    @property
    def medium_image_url(self):
        """Get medium version of book cover"""
        return ImageOptimizer.get_optimized_url(self.image_url, 'medium')
        
    @property
    def large_image_url(self):
        """Get large version of book cover"""
        return ImageOptimizer.get_optimized_url(self.image_url, 'large')

    @property
    def average_rating(self):
        if not self.reviews:
            return 0
        rating = db.session.query(func.avg(Review.rating)).filter(Review.book_id == self.id).scalar()
        return rating if rating is not None else 0

    def get_similar_books(self, limit=5):
        """Get similar books based on category and tags"""
        return Book.query.filter(
            Book.category == self.category,
            Book.id != self.id
        ).limit(limit).all()

    def get_frequently_bought_together(self, limit=3):
        """Get books frequently bought together"""
        query = text("""
            SELECT b.id, COUNT(*) as purchase_count
            FROM books b
            JOIN order_items oi1 ON b.id = oi1.book_id
            JOIN orders o1 ON oi1.order_id = o1.id
            JOIN orders o2 ON o1.user_id = o2.user_id
            JOIN order_items oi2 ON o2.id = oi2.order_id
            WHERE oi2.book_id = :book_id AND b.id != :book_id
            GROUP BY b.id
            ORDER BY purchase_count DESC
            LIMIT :limit
        """)
        result = db.session.execute(query, {'book_id': self.id, 'limit': limit})
        book_ids = [row[0] for row in result]
        return Book.query.filter(Book.id.in_(book_ids)).all()

class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    helpful_votes = db.Column(db.Integer, default=0)
    verified_purchase = db.Column(db.Boolean, default=False)

    @hybrid_property
    def user_badge(self):
        if self.verified_purchase and self.helpful_votes >= 10:
            return 'expert'
        elif self.verified_purchase:
            return 'verified'
        return 'reviewer'

class UserActivity(db.Model):
    __tablename__ = 'user_activities'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ip_address = db.Column(db.String(45))

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    payment_intent_id = db.Column(db.String(255))
    payment_status = db.Column(db.String(50), default='pending')
    payment_method = db.Column(db.String(50))
    payment_date = db.Column(db.DateTime)
    tracking_number = db.Column(db.String(100))
    carrier = db.Column(db.String(100))
    shipping_date = db.Column(db.DateTime)
    shipping_address = db.Column(db.Text)

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='SET NULL'))
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def total(self):
        return self.book.price * self.quantity

class Wishlist(db.Model):
    __tablename__ = 'wishlists'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

class ReadingList(db.Model):
    __tablename__ = 'reading_lists'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('ReadingListItem', backref='reading_list', lazy=True, cascade='all, delete-orphan')

class ReadingListItem(db.Model):
    __tablename__ = 'reading_list_items'
    id = db.Column(db.Integer, primary_key=True)
    reading_list_id = db.Column(db.Integer, db.ForeignKey('reading_lists.id', ondelete='CASCADE'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)