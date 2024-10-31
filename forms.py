from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, TextAreaField, IntegerField, SelectField, DateTimeField, BooleanField
from wtforms.validators import DataRequired, Email, Length, NumberRange, EqualTo
from datetime import datetime

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

class BookForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0)])
    description = TextAreaField('Description')
    image_url = StringField('Image URL')
    stock = IntegerField('Stock', validators=[DataRequired(), NumberRange(min=0)])
    category_id = SelectField('Category', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        super(BookForm, self).__init__(*args, **kwargs)
        from models import Category
        # Get all categories from the database
        categories = Category.query.order_by(Category.name).all()
        self.category_id.choices = [(cat.name, cat.name) for cat in categories]

class CategoryForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=50)])
    description = TextAreaField('Description')
    display_order = IntegerField('Display Order', validators=[DataRequired(), NumberRange(min=1)], default=1)
