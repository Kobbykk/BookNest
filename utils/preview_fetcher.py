import requests
from bs4 import BeautifulSoup
import logging
import re

logger = logging.getLogger(__name__)

class PreviewFetcher:
    GUTENBERG_SEARCH_URL = "https://www.gutenberg.org/ebooks/search/?query={}"
    GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes?q=isbn:{}"
    
    @staticmethod
    def clean_text(text):
        """Clean and format text content"""
        if not text:
            return ""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove ASCII art and other noise
        text = re.sub(r'[\*\_\#\[\]]+', '', text)
        return text

    @staticmethod
    def get_gutenberg_preview(title, author):
        """Try to find and fetch preview from Project Gutenberg"""
        try:
            # Search for the book
            search_query = f"{title} {author}".replace(' ', '+')
            response = requests.get(PreviewFetcher.GUTENBERG_SEARCH_URL.format(search_query))
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the first result
            result = soup.find('li', class_='booklink')
            if not result:
                return None
                
            # Get book ID
            book_link = result.find('a', href=True)
            if not book_link:
                return None
                
            book_id = book_link['href'].split('/')[-1]
            
            # Fetch the first chapter
            text_url = f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt"
            response = requests.get(text_url)
            
            if response.status_code == 200:
                # Get first 2000 characters of actual content
                content = response.text
                start_idx = content.find('*** START OF')
                if start_idx != -1:
                    content = content[start_idx:]
                    end_idx = content.find('*** END OF')
                    if end_idx != -1:
                        content = content[:end_idx]
                
                preview = PreviewFetcher.clean_text(content)[:2000]
                
                return f"""<div class="preview-content">
                    <p class="preview-source">Source: Project Gutenberg</p>
                    <div class="preview-text">{preview}</div>
                    <p class="preview-link">
                        <a href="https://www.gutenberg.org/ebooks/{book_id}" target="_blank">
                            Read full text on Project Gutenberg
                        </a>
                    </p>
                </div>"""
                
        except Exception as e:
            logger.error(f"Error fetching Gutenberg preview: {str(e)}")
        return None

    @staticmethod
    def get_google_preview(isbn):
        """Get preview from Google Books API"""
        try:
            response = requests.get(PreviewFetcher.GOOGLE_BOOKS_API_URL.format(isbn))
            if response.status_code != 200:
                return None
                
            data = response.json()
            if not data.get('items'):
                return None
                
            book_data = data['items'][0]['volumeInfo']
            preview_text = book_data.get('description', '')
            if not preview_text:
                return None
                
            preview_text = PreviewFetcher.clean_text(preview_text)
            
            # Get Google Books preview link if available
            preview_link = book_data.get('previewLink', '')
            preview_html = f"""<div class="preview-content">
                <p class="preview-source">Source: Google Books</p>
                <div class="preview-text">{preview_text}</div>"""
                
            if preview_link:
                preview_html += f"""
                <p class="preview-link">
                    <a href="{preview_link}" target="_blank">View on Google Books</a>
                </p>"""
                
            preview_html += "</div>"
            return preview_html
            
        except Exception as e:
            logger.error(f"Error fetching Google Books preview: {str(e)}")
        return None

    @classmethod
    def get_preview_content(cls, book):
        """Get preview content from available sources"""
        # Try Project Gutenberg first
        preview = cls.get_gutenberg_preview(book.title, book.author)
        
        # Fall back to Google Books if no Gutenberg content
        if not preview and book.isbn:
            preview = cls.get_google_preview(book.isbn)
            
        return preview or """<div class="preview-content">
            <p class="preview-unavailable">
                Preview not available for this book.
            </p>
        </div>"""
