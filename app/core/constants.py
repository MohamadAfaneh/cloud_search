from enum import Enum

class FileExtension(str, Enum):
    """File extensions supported by the application."""
    TXT = '.txt'
    PDF = '.pdf'
    CSV = '.csv'
    PNG = '.png'

SUPPORTED_EXTENSIONS = [ext.value.lstrip('.') for ext in FileExtension] 


API = 'api'
V1 = 'v1'