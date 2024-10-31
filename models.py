from app import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
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
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    display_order = db.Column(db.Integer, default=0)
    books = db.relationship('Book', backref='category_ref', lazy=True)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    author = db.Column(db.String(100), nullable=False, index=True)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    stock = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50), db.ForeignKey('category.name', onupdate='CASCADE', ondelete='SET NULL', name='fk_book_category'))
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
        if not self.reviews:
            return 0
        return sum(review.rating for review in self.reviews) / len(self.reviews)

    @property
    def current_price(self):
        active_discount = BookDiscount.query.filter(
            BookDiscount.book_id == self.id,
            BookDiscount.active == True,
            BookDiscount.end_date >= datetime.utcnow()
        ).first()
        if active_discount:
            return self.price * (1 - active_discount.discount.percentage / 100)
        return self.price

class Discount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    percentage = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    active = db.Column(db.Boolean, default=True)
    books = db.relationship('BookDiscount', backref='discount', lazy=True, cascade='all, delete-orphan')

    __table_args__ = (
        db.CheckConstraint('percentage >= 0 AND percentage <= 100', name='check_valid_percentage'),
        db.CheckConstraint('end_date > start_date', name='check_valid_date_range'),
    )

class BookDiscount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id', ondelete='CASCADE', name='fk_book_discount_book'), nullable=False)
    discount_id = db.Column(db.Integer, db.ForeignKey('discount.id', ondelete='CASCADE', name='fk_book_discount_discount'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    active = db.Column(db.Boolean, default=True)
    
    __table_args__ = (
        db.CheckConstraint('end_date > start_date', name='check_valid_date_range'),
        db.Index('idx_book_discount_dates', 'start_date', 'end_date'),
    )

class Order(db.Model):
    STATUS_CHOICES = ['pending', 'in_process', 'payment_pending', 'completed', 'approved']
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', name='fk_order_user'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    total = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

    __table_args__ = (
        db.CheckConstraint(status.in_(STATUS_CHOICES), name='check_valid_status'),
        db.CheckConstraint('total >= 0', name='check_positive_total'),
    )

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id', ondelete='CASCADE', name='fk_order_item_order'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id', ondelete='SET NULL', name='fk_order_item_book'), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    __table_args__ = (
        db.CheckConstraint('quantity > 0', name='check_positive_quantity'),
        db.CheckConstraint('price >= 0', name='check_valid_price'),
    )

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', name='fk_review_user'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id', ondelete='CASCADE', name='fk_review_book'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.CheckConstraint('rating >= 1 AND rating <= 5', name='check_valid_rating'),
        db.UniqueConstraint('user_id', 'book_id', name='unique_user_book_review'),
    )

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', name='fk_cart_item_user'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id', ondelete='CASCADE', name='fk_cart_item_book'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.CheckConstraint('quantity > 0', name='check_positive_quantity'),
        db.Index('idx_cart_user_book', 'user_id', 'book_id', unique=True),
    )

class UserActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', name='fk_user_activity_user'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ip_address = db.Column(db.String(45))
