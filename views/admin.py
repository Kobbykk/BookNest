from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Book
from forms import BookForm
from app import db

admin = Blueprint('admin', __name__)

@admin.route('/admin')
@login_required
def dashboard():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))
    books = Book.query.all()
    return render_template('admin/dashboard.html', books=books)

@admin.route('/admin/book/add', methods=['GET', 'POST'])
@login_required
def add_book():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))
    
    form = BookForm()
    if form.validate_on_submit():
        book = Book(
            title=form.title.data,
            author=form.author.data,
            price=form.price.data,
            description=form.description.data,
            image_url=form.image_url.data,
            stock=form.stock.data
        )
        db.session.add(book)
        db.session.commit()
        flash('Book added successfully.')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/book_form.html', form=form, title='Add Book')
