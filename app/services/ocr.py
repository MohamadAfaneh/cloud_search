from PIL import Image
import pytesseract
from typing import Optional
import logging
import os
import asyncio
from ..core.config import get_settings

logger = logging.getLogger(__name__)

class OCRService:
    """
    Service for performing OCR on images.
    
    """
    
    def __init__(self):
        """
        Initialize the OCR service.
        
        """
        self.settings = get_settings()
        self.tesseract_cmd = self.settings.TESSERACT_CMD
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        logger.info(f"OCR service initialized with Tesseract command: {self.tesseract_cmd}")
    
    def _extract_text_sync(self, image_path: str) -> str:
        """
        Synchronously extract text from an image file.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            str: Extracted text from the image
        """
        try:
            logger.info(f"Opening image file: {image_path}")
            # Open and process the image
            image = Image.open(image_path)
            logger.info(f"Image size: {image.size}, format: {image.format}")
            
            # Extract text using pytesseract
            logger.info("Starting OCR process")
            text = pytesseract.image_to_string(image, lang=self.settings.OCR_LANGUAGE)
            
            if not text.strip():
                logger.warning(f"No text extracted from image: {image_path}")
            else:
                logger.info(f"Successfully extracted {len(text)} characters from image")
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error in OCR processing for {image_path}: {e}")
            raise

    async def extract_text_from_png(self, image_path: str) -> str:
        """
        Asynchronously extract text from an image file.
        """
        try:
            logger.info(f"Starting async OCR for image: {image_path}")
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, self._extract_text_sync, image_path)
            return text
        except Exception as e:
            logger.error(f"Error extracting text from {image_path}: {e}")
            raise


_ocr_service = None

def get_ocr_service() -> OCRService:
    """
    Get or create a singleton instance of OCRService.
    """
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service