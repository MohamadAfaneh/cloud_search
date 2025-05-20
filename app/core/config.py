from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List, Optional
from pathlib import Path
import os
import sys
from .constants import SUPPORTED_EXTENSIONS

class Settings(BaseSettings):
    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    
    # Storage settings
    STORAGE_PROVIDER: str = "dropbox"
    DROPBOX_ACCESS_TOKEN: str
    DOWNLOAD_FOLDER: Path = Path("/app/downloads") 
    KNOWN_FILES_PATH: Path = Path("/app/data/known_files.json")  
    
    # Elasticsearch settings
    ELASTICSEARCH_HOST: str = "elasticsearch"
    ELASTICSEARCH_USER: str = None
    ELASTICSEARCH_PASSWORD: str = None
    ELASTICSEARCH_VERIFY_CERTS: bool = False
    ELASTICSEARCH_INDEX: str = "cloud_search"
    
    # OCR settings
    TESSERACT_CMD: str = "/usr/bin/tesseract"
    OCR_LANGUAGE: str = "eng"  
    
    # Search settings
    MAX_FILE_SIZE: int = 600000  
    SUPPORTED_FORMATS: List[str] = SUPPORTED_EXTENSIONS
    USE_CACHE: bool = True  
    
    # API settings
    API_VERSION: str = "v1"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False

    def validate(self):
        assert self.DROPBOX_ACCESS_TOKEN, "missing the value of DROPBOX_ACCESS_TOKEN in .env file"
        
        # Create directories for downalods and konwn_files.json
        self.DOWNLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        self.KNOWN_FILES_PATH.parent.mkdir(parents=True, exist_ok=True)

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    settings = Settings()
    try:
        settings.validate()
    except Exception as e:
        print(f"Configuration Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    return settings 