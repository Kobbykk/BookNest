from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, TextAreaField, IntegerField, SelectField, DateTimeField, BooleanField, FieldList, FormField
from wtforms.validators import DataRequired, Email, Length, NumberRange, EqualTo
from datetime import datetime
from models import Category

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Length(min=6)], description="Leave blank to keep current password")
    role = SelectField('Role', choices=[
        ('customer', 'Customer'),
        ('editor', 'Editor'),
        ('manager', 'Manager'),
        ('admin', 'Admin')
    ], validators=[DataRequired()])

class ProfileUpdateForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', 
                                   validators=[EqualTo('new_password', message='Passwords must match')])

class ReviewForm(FlaskForm):
    rating = IntegerField('Rating', validators=[DataRequired(), NumberRange(min=1, max=5)])
    comment = TextAreaField('Review', validators=[DataRequired(), Length(min=10, max=500)])

class BookFormatForm(FlaskForm):
    format_type = SelectField('Format Type', choices=[
        ('hardcover', 'Hardcover'),
        ('paperback', 'Paperback'),
        ('ebook', 'E-book')
    ], validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0)])
    stock = IntegerField('Stock', validators=[DataRequired(), NumberRange(min=0)])
    isbn = StringField('ISBN', validators=[Length(max=13)])

class BookForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0)])
    description = TextAreaField('Description')
    image_url = StringField('Image URL')
    stock = IntegerField('Stock', validators=[DataRequired(), NumberRange(min=0)])
    category = SelectField('Category', validators=[DataRequired()])
    is_featured = BooleanField('Featured on Homepage')
    formats = FieldList(FormField(BookFormatForm), min_entries=1)

    def __init__(self, *args, **kwargs):
        super(BookForm, self).__init__(*args, **kwargs)
        # Get categories from database
        categories = [(cat.name, cat.name) for cat in Category.query.order_by(Category.display_order).all()]
        # Add default categories if none exist
        default_categories = [
            'Programming', 'Data Science', 'Web Development', 'Database',
            'AI', 'Computer Science', 'Software Engineering'
        ]
        existing_categories = {cat[0] for cat in categories}
        for cat in default_categories:
            if cat not in existing_categories:
                categories.append((cat, cat))
        self.category.choices = sorted(set(categories))

class CategoryForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=50)])
    description = TextAreaField('Description')
    display_order = IntegerField('Display Order', validators=[DataRequired(), NumberRange(min=1)], default=1)
    old_category = StringField('Old Category Name')  # For category renaming
