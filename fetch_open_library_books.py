import os
import requests
import time
from datetime import datetime
from flask import Flask
from models import Book, Category, BookFormat
from app import app, db
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUBJECTS = [
    'programming_languages',
    'computer_science',
    'data_science',
    'artificial_intelligence',
    'software_engineering',
    'web_development',
    'database_management',
    'algorithms'
]

def ensure_categories_exist():
    """Ensure all required categories exist in the database"""
    categories = {}
    try:
        for subject in SUBJECTS:
            category_name = subject.replace('_', ' ').title()
            existing_category = Category.query.filter_by(name=category_name).first()
            if not existing_category:
                new_category = Category(
                    name=category_name,
                    description=f"Books about {category_name.lower()}",
                    display_order=SUBJECTS.index(subject)
                )
                db.session.add(new_category)
                db.session.flush()  # Get the ID without committing
                categories[subject] = new_category
            else:
                categories[subject] = existing_category
        
        db.session.commit()
        logger.info("Categories created successfully")
        return categories
    except Exception as e:
        logger.error(f"Error creating categories: {str(e)}")
        db.session.rollback()
        raise

def get_book_details(work_key):
    """Fetch detailed book information from Open Library API"""
    time.sleep(1)  # Rate limiting
    url = f"https://openlibrary.org{work_key}.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching book details for {work_key}: {str(e)}")
    return None

def get_book_editions(work_id):
    """Fetch all editions for a work"""
    time.sleep(1)  # Rate limiting
    url = f"https://openlibrary.org/works/{work_id}/editions.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get('entries', [])
    except Exception as e:
        logger.error(f"Error fetching editions for {work_id}: {str(e)}")
        return []

def get_book_isbn(editions):
    """Try to get ISBN from multiple editions"""
    for edition in editions:
        try:
            # Try ISBN-13 first
            if 'isbn_13' in edition:
                return edition['isbn_13'][0]
            # Then try ISBN-10
            if 'isbn_10' in edition:
                return edition['isbn_10'][0]
        except (KeyError, IndexError):
            continue
    return None

def parse_date(date_str):
    """Parse publication date with multiple format support"""
    if not date_str:
        return datetime.now()
        
    date_formats = ['%Y', '%Y-%m-%d', '%B %Y', '%Y/%m/%d', '%d/%m/%Y']
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return datetime.now()

def fetch_and_add_books():
    """Fetch books from Open Library API and add them to the database"""
    logger.info("Starting book fetch process...")
    
    try:
        logger.info("Setting up categories...")
        categories = ensure_categories_exist()
        
        logger.info("Fetching books from Open Library...")
        added_books = 0
        
        for subject in SUBJECTS:
            logger.info(f"Fetching books for subject: {subject}")
            url = f"https://openlibrary.org/subjects/{subject}.json?limit=20&published_in=2000-2024"
            
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                
                for work in data.get('works', []):
                    if added_books >= 25:  # Add a few extra in case some fail
                        break
                        
                    try:
                        # Get detailed work information
                        work_id = work['key'].split('/')[-1]
                        work_details = get_book_details(work['key'])
                        if not work_details:
                            continue
                        
                        # Get all editions and find ISBN
                        editions = get_book_editions(work_id)
                        isbn = get_book_isbn(editions)
                        
                        if not isbn:
                            logger.warning(f"No ISBN found for book: {work['title']}")
                            continue
                        
                        # Check if book already exists
                        existing_book = Book.query.filter_by(isbn=isbn).first()
                        if existing_book:
                            logger.info(f"Book already exists: {work['title']}")
                            continue
                        
                        # Get category
                        category = categories[subject]
                        if not category:
                            logger.warning(f"Category not found for subject: {subject}")
                            continue
                        
                        # Calculate price based on page count or use default
                        base_price = 29.99
                        page_count = work_details.get('number_of_pages', 300)
                        if page_count:
                            base_price = min(19.99 + (page_count * 0.05), 99.99)
                        
                        # Get the first edition's publication date
                        pub_date = parse_date(editions[0].get('publish_date') if editions else None)
                        
                        # Create new book instance
                        book = Book()
                        book.title = work['title']
                        book.author = work.get('authors', [{'name': 'Unknown'}])[0].get('name', 'Unknown')
                        book.price = base_price
                        book.description = work_details.get('description', {}).get('value', '') if isinstance(work_details.get('description'), dict) else work_details.get('description', '')
                        book.image_url = f"https://covers.openlibrary.org/b/id/{work['cover_id']}-L.jpg" if 'cover_id' in work else None
                        book.stock = 50
                        book.category = category.name
                        book.isbn = isbn
                        book.publisher = editions[0].get('publishers', ['Unknown Publisher'])[0] if editions and editions[0].get('publishers') else 'Unknown Publisher'
                        book.publication_date = pub_date
                        book.page_count = page_count
                        book.language = editions[0].get('languages', [{'key': '/languages/eng'}])[0]['key'].split('/')[-1] if editions and editions[0].get('languages') else 'eng'
                        book.tags = ','.join(work_details.get('subjects', [])[:5]) if 'subjects' in work_details else ''
                        book.is_featured = False
                        
                        # Add book formats
                        for format_type, price_adj, stock, suffix in [
                            ('hardcover', 10, 50, 'H'),
                            ('paperback', 0, 100, 'P'),
                            ('ebook', -10, 999, 'E')
                        ]:
                            book_format = BookFormat()
                            book_format.format_type = format_type
                            book_format.price = max(base_price + price_adj, 9.99)
                            book_format.stock = stock
                            book_format.isbn = f"{isbn}-{suffix}"
                            book.formats.append(book_format)
                        
                        # Add to database
                        db.session.add(book)
                        db.session.commit()
                        added_books += 1
                        logger.info(f"Added book: {book.title}")
                        
                    except Exception as e:
                        logger.error(f"Error adding book: {str(e)}")
                        db.session.rollback()
                        continue
                    
                if added_books >= 25:
                    break
                    
            except Exception as e:
                logger.error(f"Error processing subject {subject}: {str(e)}")
                continue
        
        logger.info(f"Successfully added {added_books} books")
        return added_books
        
    except Exception as e:
        logger.error(f"Critical error in fetch_and_add_books: {str(e)}")
        return 0

if __name__ == "__main__":
    with app.app_context():
        fetch_and_add_books()
