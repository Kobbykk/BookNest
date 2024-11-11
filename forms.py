from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, TextAreaField, IntegerField, SelectField, DateTimeField, BooleanField, FieldList, FormField
from wtforms.validators import DataRequired, Email, Length, NumberRange, EqualTo, Optional, ValidationError
from datetime import datetime
import re

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

def validate_isbn(form, field):
    """Custom validator for ISBN field"""
    if field.data:
        # Remove any hyphens or spaces
        isbn = re.sub(r'[-\s]', '', field.data)
        # Check if it's a valid ISBN-10 or ISBN-13
        if not (len(isbn) == 10 or len(isbn) == 13) or not isbn.isdigit():
            raise ValidationError('Invalid ISBN format. Must be 10 or 13 digits.')

class BookFormatForm(FlaskForm):
    format_type = SelectField('Format Type', choices=[
        ('hardcover', 'Hardcover'),
        ('paperback', 'Paperback'),
        ('ebook', 'E-book')
    ], validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0.01, message="Price must be greater than 0")])
    stock = IntegerField('Stock', validators=[DataRequired(), NumberRange(min=0)])
    isbn = StringField('ISBN', validators=[Optional(), validate_isbn])

class BookForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=1, max=200)])
    author = StringField('Author', validators=[DataRequired(), Length(min=1, max=100)])
    price = FloatField('Price', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Price must be greater than 0")
    ])
    description = TextAreaField('Description', validators=[Optional(), Length(max=2000)])
    image_url = StringField('Image URL', validators=[Optional(), Length(max=500)])
    stock = IntegerField('Stock', validators=[DataRequired(), NumberRange(min=0)])
    category_id = SelectField('Category', validators=[DataRequired()])
    is_featured = BooleanField('Featured on Homepage')
    isbn = StringField('ISBN', validators=[Optional(), validate_isbn])
    publisher = StringField('Publisher', validators=[Optional(), Length(max=100)])
    publication_date = DateTimeField('Publication Date', format='%Y-%m-%d', validators=[Optional()])
    page_count = IntegerField('Page Count', validators=[Optional(), NumberRange(min=1)])
    language = StringField('Language', validators=[Optional(), Length(max=50)])
    tags = StringField('Tags', validators=[Optional(), Length(max=200)])
    series_id = SelectField('Series', validators=[Optional()], coerce=int)
    series_order = IntegerField('Series Order', validators=[Optional(), NumberRange(min=1)])
    formats = FieldList(FormField(BookFormatForm), min_entries=1)

    def __init__(self, *args, **kwargs):
        super(BookForm, self).__init__(*args, **kwargs)
        from models import Category, BookSeries
        
        # Set up category choices
        categories = Category.query.order_by(Category.name).all()
        self.category_id.choices = [(cat.name, cat.name) for cat in categories]
        
        # Set up series choices
        series_list = BookSeries.query.order_by(BookSeries.title).all()
        self.series_id.choices = [(0, 'None')] + [(s.id, s.title) for s in series_list]

class CategoryForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=50)])
    description = TextAreaField('Description')
    display_order = IntegerField('Display Order', validators=[DataRequired(), NumberRange(min=1)], default=1)
