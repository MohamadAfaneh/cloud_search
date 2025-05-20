from typing import Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from elasticsearch import AsyncElasticsearch
from elastic_transport import Transport
import os
import logging
import fitz 
import csv
from functools import wraps
from ..core.config import get_settings
from ..core.constants import FileExtension
from .ocr import get_ocr_service

from ..models.searchResponse import Full_path_SearchResponse

logger = logging.getLogger(__name__)

class Textsearch:
    """
    Base class for text search functionality.
    """
    
    def __init__(self, provider: str):
        """
        Initialize the text search service.
        """
        self.provider = provider
        self.settings = get_settings()
        logger.info(f"Initializing search service: {provider}")

class ElasticSearchService(Textsearch):
    """
    Elasticsearch implementation of the text search service.
    """
    
    def __init__(self):
        """
        Initialize the Elasticsearch service.
        """
        super().__init__('elasticsearch')
        self.client = AsyncElasticsearch(
            hosts=[self.settings.ELASTICSEARCH_HOST],
            basic_auth=(self.settings.ELASTICSEARCH_USER, self.settings.ELASTICSEARCH_PASSWORD) if self.settings.ELASTICSEARCH_USER else None,
            verify_certs=self.settings.ELASTICSEARCH_VERIFY_CERTS
        )
        self.index_name = self.settings.ELASTICSEARCH_INDEX
        self.downloads_folder = self.settings.DOWNLOAD_FOLDER
        logger.info("Elasticsearch service initialized successfully")

    async def index_file(self, path: str, content: str, provider: str, extension: str, last_modified: datetime):
        """
        Index a file in Elasticsearch.
        """
        try:
            doc_id = f"{provider}:{path}"
            
            # Convert content to string if it's bytes
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='ignore')
            
            doc = {
                "file_path": path,
                "provider": provider,
                "content": content,
                "extension": extension,
                "last_modified": last_modified.isoformat(),
                "size": len(content.encode('utf-8')) if isinstance(content, str) else len(content)
            }
            
            await self.client.index(
                index=self.index_name,
                id=doc_id,
                document=doc,
                refresh=True
            )
            logger.info(f"Indexed file: {doc_id}")
            
        except Exception as e:
            logger.error(f"Error indexing file {path}: {str(e)}")
            raise Exception(f"Failed to index file: {str(e)}")

    def _create_index(self):
        """
        Create the Elasticsearch index if it doesn't exist.
        """
        try:
            if not self.client.indices.exists(index=self.index_name):
                mapping = {
                    "mappings": {
                        "properties": {
                            "file_path": {"type": "keyword"},
                            "provider": {"type": "keyword"},
                            "content": {
                                "type": "text",
                                "analyzer": "standard",
                                "search_analyzer": "standard"
                            },
                            "last_modified": {"type": "date"},
                            "size": {"type": "long"},
                            "metadata": {"type": "object"}
                        }
                    },
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "index": {
                            "refresh_interval": "1s"
                        }
                    }
                }
                self.client.indices.create(index=self.index_name, body=mapping)
                logger.info(f"Created Elasticsearch index: {self.index_name}")
        except Exception as e:
            logger.error(f"Error creating Elasticsearch index: {e}")
            raise Exception(f"Failed to create index: {str(e)}")

    def validate_file_size(self, file_path: str) -> bool:
        """
        Check if file size is within the configured limits.
        """
        try:
            size = os.path.getsize(file_path)
            return size <= self.settings.MAX_FILE_SIZE
        except OSError as e:
            logger.error(f"Error checking file size for {file_path}: {e}")
            return False

    def validate_file_type(self, file_path: str) -> bool:
        """
        Check if file type is supported for indexing.
        """
        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        return ext in self.settings.SUPPORTED_FORMATS

    async def extract_text_from_file(self, file_path: str) -> str:
        """
        Extract text content from various file formats.

        Supported formats = PDF, TXT , CSV , PNG
        """
        if not self.validate_file_size(file_path):
            raise Exception(f"File {file_path} exceeds maximum size limit")

        if not self.validate_file_type(file_path):
            raise Exception(f"Unsupported file type for {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        logger.info(f"Extracting text from {file_path} (type: {ext})")
        
        try:
            
            if ext == FileExtension.PDF:
                text = ""
                try:
                    with fitz.open(file_path) as pdf:
                        for page in pdf:
                            text += page.get_text()
                    if not text.strip():
                        logger.warning(f"No text extracted from PDF: {file_path}")
                    return text
                except Exception as e:
                    logger.error(f"Error extracting text from PDF {file_path}: {str(e)}")
                    raise Exception(f"PDF text extraction failed: {str(e)}")
            
            elif ext == FileExtension.PNG:
                try:
                    logger.info(f"Starting OCR on image: {file_path}")
                    ocr_service = get_ocr_service()
                    text = await ocr_service.extract_text_from_png(file_path)
                    if not text:
                        logger.warning(f"No text extracted from image: {file_path}")
                    else:
                        logger.info(f"Successfully extracted {len(text)} characters from image")
                    return text
                except Exception as e:
                    logger.error(f"Error extracting text from image {file_path}: {str(e)}")
                    raise Exception(f"Image text extraction failed: {str(e)}")
            
            elif ext == FileExtension.CSV:
                try:
                    text = []
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as csvfile:
                        reader = csv.reader(csvfile)
                        for row in reader:
                            text.append(' '.join(str(cell) for cell in row))
                    return '\n'.join(text)
                except Exception as e:
                    logger.error(f"Error extracting text from CSV file {file_path}: {str(e)}")
                    raise Exception(f"Failed to extract from CSV file: {str(e)}")
            
            else:
                raise Exception(f"Unsupported file type: {ext}")
                
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            raise Exception(f"Text extraction failed: {str(e)}")

    async def search_files(self, query: str) -> Full_path_SearchResponse:
        """
        Search for text in indexed files.
        """
        try:
            search_body = {
                "query": {
                    "bool": {
                        "should": [
                            {"match": {"content": {"query": query, "operator": "and"}}},
                            {"match": {"file_path": {"query": query, "operator": "and"}}},
                            {"match": {"provider": {"query": query, "operator": "and"}}},
                            {"match": {"extension": {"query": query, "operator": "and"}}},
                            {"match": {"last_modified": {"query": query, "operator": "and"}}},
                            {"match": {"size": {"query": query, "operator": "and"}}}
                        ],
                        "minimum_should_match": 1
                    }
                },
                "highlight": {
                    "fields": {
                        "content": {
                            "number_of_fragments": 3,
                            "fragment_size": 150,
                            "pre_tags": ["<mark>"],
                            "post_tags": ["</mark>"]
                        }
                    }
                },
                "sort": [
                    {"_score": {"order": "desc"}},
                    {"last_modified": {"order": "desc"}}
                ]
            }
            response = await self.client.search(index=self.index_name, body=search_body)
            total_hits = response["hits"]["total"]["value"]
            results = []
            for hit in response["hits"]["hits"]:
                try:
                    file_path = hit["_source"]["file_path"]
                    full_path = f"{hit['_source']['provider'][0].upper()}../{os.path.basename(file_path)}"
                    
                    result = {
                        "full_path": full_path,
                        "file_path": file_path,
                        "provider": hit["_source"]["provider"],
                        "score": hit["_score"],
                        "last_modified": hit["_source"]["last_modified"],
                        "size": hit["_source"]["size"],
                        "highlights": hit.get("highlight", {}).get("content", [])
                    }
                    results.append(result)
                except KeyError as e:
                    logger.warning(f"Skipping malformed search result: {str(e)}")
                    continue
            
            return Full_path_SearchResponse(
                results=results,
                total_hits=total_hits
            )
            
        except Exception as e:
            logger.error(f"Error searching files: {str(e)}")
            raise Exception(f"Search operation failed: {str(e)}")

    async def _delete_missing_from_index(self, current_files: set):
        """
        Delete index of documents that no longer exist in cloud storage.
        
        """
        try:
            response = await self.client.search(
                index=self.index_name,
                body={
                    "query": {"match_all": {}},
                    "size": 1000,
                    "_source": ["file_path", "provider"]
                }
            )
            
            for hit in response["hits"]["hits"]:
                file_path = hit["_source"]["file_path"]
                provider = hit["_source"].get("provider", self.provider)
                doc_id = f"{provider}:{file_path}"
                
                if doc_id not in current_files:
                    try:
                        await self.client.delete(index=self.index_name,id=doc_id,refresh=True)                        
                        logger.info(f"Delete file from index: {file_path}")
    
                    except Exception as e:
                        logger.error(f"Error deleting {file_path}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error cleaning up index: {str(e)}")
            raise Exception(f"Failed to clean up index: {str(e)}")

    async def update_index_from_local_folder(self):
        """
        Update Elasticsearch index from local folder.
        """
        try:
            current_files = set()
            storage_provider = self.provider
            
            for root, dirs, files in os.walk(self.downloads_folder):
                for file in files:
                    local_path = os.path.join(root, file)
                    
                    try:
                        if not self.validate_file_size(local_path):
                            logger.warning(f"Skipping {local_path}: File too large")
                            continue
                            
                        if not self.validate_file_type(local_path):
                            logger.warning(f"Skipping {local_path}: Unsupported file type")
                            continue
                        
                        rel_path = os.path.relpath(local_path, self.downloads_folder)
                        file_id = f"{storage_provider}:{rel_path}"
                        current_files.add(file_id)

                        content = await self.extract_text_from_file(local_path)
                        if not content or not content.strip():
                            logger.warning(f"No content extracted from {local_path}")
                            continue

                        stat = os.stat(local_path)
                        
                        doc = {
                            "file_path": rel_path,
                            "provider": storage_provider,
                            "content": content,
                            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "size": stat.st_size,
                        }
                        logger.info(f"Indexing document for {rel_path} with content length: {len(content)}")
                        
                        await self.client.index(
                            index=self.index_name,
                            id=file_id,
                            document=doc,
                            refresh=True
                        )
                        logger.info(f"Indexed file: {file_id}")
                        
                    except Exception as e:
                        logger.error(f"Error processing file {local_path}: {str(e)}")
                        continue

            await self._delete_missing_from_index(current_files)
            
        except Exception as e:
            logger.error(f"Error updating index: {str(e)}")
            raise Exception(f"Failed to update index: {str(e)}")

    async def close(self):
        """
        Close the Elasticsearch client connection.
        """
        try:
            await self.client.close()
            logger.info("Elasticsearch client connection closed")
        except Exception as e:
            logger.error(f"Error closing Elasticsearch client: {e}")


_es_service = None

def get_elasticsearch_service() -> ElasticSearchService:
    """
    Get or create a singleton instance of ElasticSearchService.
    
    Returns:
        ElasticSearchService: The singleton instance of the Elasticsearch service
    """
    global _es_service
    if _es_service is None:
        _es_service = ElasticSearchService()
    return _es_service 