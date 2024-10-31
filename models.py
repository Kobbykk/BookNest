from app import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import func

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='user', lazy=True, cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='user', lazy=True, cascade='all, delete-orphan')
    cart_items = db.relationship('CartItem', backref='user', lazy=True, cascade='all, delete-orphan')
    activities = db.relationship('UserActivity', backref='user', lazy=True, cascade='all, delete-orphan')

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    display_order = db.Column(db.Integer, default=0)
    books = db.relationship('Book', backref='category_ref', lazy=True)

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
    discounts = db.relationship('BookDiscount', backref='book', lazy=True, cascade='all, delete-orphan')
    cart_items = db.relationship('CartItem', backref='book', lazy=True, cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', backref='book', lazy=True)

    __table_args__ = (
        db.CheckConstraint('price >= 0', name='check_positive_price'),
        db.CheckConstraint('stock >= 0', name='check_non_negative_stock'),
    )

    @property
    def average_rating(self):
        """Calculate the average rating for the book from all reviews."""
        if not self.reviews:
            return 0.0
        return db.session.query(func.avg(Review.rating)).filter(Review.book_id == self.id).scalar() or 0.0

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    
    # Payment related fields
    payment_intent_id = db.Column(db.String(255))  # Removed unique and index constraints
    payment_status = db.Column(db.String(50), default='pending')
    payment_method = db.Column(db.String(50))
    payment_date = db.Column(db.DateTime)
    
    # Shipping related fields
    tracking_number = db.Column(db.String(100))
    carrier = db.Column(db.String(100))
    shipping_date = db.Column(db.DateTime)
    shipping_address = db.Column(db.Text)

    __table_args__ = (
        db.CheckConstraint('total >= 0', name='check_positive_total'),
    )

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='SET NULL'))
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    __table_args__ = (
        db.CheckConstraint('quantity > 0', name='check_order_positive_quantity'),
        db.CheckConstraint('price >= 0', name='check_order_valid_price'),
    )

class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.CheckConstraint('rating >= 1 AND rating <= 5', name='check_review_valid_rating'),
        db.UniqueConstraint('user_id', 'book_id', name='uq_user_book_review'),
    )

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.CheckConstraint('quantity > 0', name='check_cart_positive_quantity'),
        db.UniqueConstraint('user_id', 'book_id', name='uq_user_book_cart'),
    )

    @property
    def total(self):
        return self.book.price * self.quantity

class UserActivity(db.Model):
    __tablename__ = 'user_activities'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ip_address = db.Column(db.String(45))

class Discount(db.Model):
    __tablename__ = 'discounts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    percentage = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    active = db.Column(db.Boolean, default=True)
    books = db.relationship('BookDiscount', backref='discount', lazy=True, cascade='all, delete-orphan')

    __table_args__ = (
        db.CheckConstraint('percentage >= 0 AND percentage <= 100', name='check_discount_valid_percentage'),
        db.CheckConstraint('end_date > start_date', name='check_discount_valid_date_range'),
    )

class BookDiscount(db.Model):
    __tablename__ = 'book_discounts'
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    discount_id = db.Column(db.Integer, db.ForeignKey('discounts.id', ondelete='CASCADE'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    active = db.Column(db.Boolean, default=True)

    __table_args__ = (
        db.CheckConstraint('end_date > start_date', name='check_bookdiscount_valid_date_range'),
        db.UniqueConstraint('book_id', 'discount_id', name='uq_book_discount'),
    )
