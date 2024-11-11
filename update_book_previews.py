from app import app, db
from models import Book
from utils.preview_fetcher import PreviewFetcher
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_book_previews():
    """Update all books with preview content"""
    with app.app_context():
        try:
            books = Book.query.all()
            updated_count = 0
            
            for book in books:
                if not book.preview_content:
                    logger.info(f"Fetching preview for: {book.title}")
                    preview = PreviewFetcher.get_preview_content(book)
                    if preview:
                        book.preview_content = preview
                        db.session.add(book)
                        updated_count += 1
                        
                        # Commit every 5 books to avoid long transactions
                        if updated_count % 5 == 0:
                            db.session.commit()
                            logger.info(f"Updated {updated_count} books so far")
            
            db.session.commit()
            logger.info(f"Successfully updated {updated_count} books with preview content")
            
        except Exception as e:
            logger.error(f"Error updating book previews: {str(e)}")
            db.session.rollback()
            raise e

if __name__ == "__main__":
    update_book_previews()
