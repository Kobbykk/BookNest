import os
import hashlib
from io import BytesIO
import requests
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class ImageOptimizer:
    SIZES = {
        'thumbnail': (150, 150),
        'medium': (300, 300),
        'large': (600, 600)
    }
    
    QUALITY = 85  # Default JPEG quality
    
    @staticmethod
    def get_optimized_path(url, size):
        """Generate a path for the optimized version of an image"""
        if not url:
            return None
            
        # Create hash of URL to use as filename
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        # Get file extension (default to .jpg)
        ext = os.path.splitext(url)[-1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
            ext = '.jpg'
            
        # Create path
        return f"static/optimized/{size}/{url_hash}{ext}"
        
    @staticmethod
    def ensure_dirs():
        """Ensure optimization directories exist"""
        for size in ImageOptimizer.SIZES.keys():
            os.makedirs(f"static/optimized/{size}", exist_ok=True)
    
    @staticmethod
    def fetch_image(url):
        """Fetch image from URL"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return Image.open(BytesIO(response.content))
        except Exception as e:
            logger.error(f"Error fetching image from {url}: {str(e)}")
            return None
    
    @staticmethod
    def optimize_image(image, size):
        """Optimize image for given size"""
        target_size = ImageOptimizer.SIZES[size]
        
        # Convert image to RGB if it's not
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Calculate new size maintaining aspect ratio
        ratio = min(target_size[0]/image.size[0], target_size[1]/image.size[1])
        new_size = tuple([int(x*ratio) for x in image.size])
        
        # Resize image using high-quality Lanczos resampling
        resized = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Create new image with padding if needed
        final = Image.new("RGB", target_size, (255, 255, 255))
        paste_pos = ((target_size[0] - new_size[0])//2,
                    (target_size[1] - new_size[1])//2)
        final.paste(resized, paste_pos)
        
        return final
    
    @classmethod
    def get_optimized_url(cls, url, size='medium'):
        """Get optimized version of image, creating if needed"""
        if not url:
            return url
            
        # Ensure size is valid
        if size not in cls.SIZES:
            size = 'medium'
            
        # Get path for optimized version
        opt_path = cls.get_optimized_path(url, size)
        if not opt_path:
            return url
            
        # If optimized version exists, return its URL
        if os.path.exists(opt_path):
            return f"/{opt_path}"
            
        try:
            # Ensure directories exist
            cls.ensure_dirs()
            
            # Fetch original image
            image = cls.fetch_image(url)
            if not image:
                return url
                
            # Optimize image
            optimized = cls.optimize_image(image, size)
            
            # Save optimized version with compression
            optimized.save(opt_path, "JPEG", 
                         quality=cls.QUALITY, 
                         optimize=True,
                         progressive=True)
            
            return f"/{opt_path}"
            
        except Exception as e:
            logger.error(f"Error optimizing image: {str(e)}")
            return url
