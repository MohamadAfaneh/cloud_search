import os
from typing import Dict, Any
import json
import logging
from datetime import datetime
from ..services.storage import get_storage_service
from ..core.config import get_settings
from .textsearch import ElasticSearchService

logger = logging.getLogger(__name__)

class SearchService():
    """
    Service class for handling search operations in cloud storage files.
    """
    
    def __init__(self):
        """
        Initialize the SearchService with required settings and services.
        """
        self.settings = get_settings()
        self.search_provider = ElasticSearchService()
        self.known_files_path = self.settings.KNOWN_FILES_PATH
        self.download_folder = self.settings.DOWNLOAD_FOLDER
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(self.known_files_path), exist_ok=True)
        os.makedirs(self.download_folder, exist_ok=True)

    def create_load_known_files(self) -> Dict:
        """
        Load known files from JSON file or create empty dict if file doesn't exist.
        """
        try:
            if os.path.exists(self.known_files_path):
                with open(self.known_files_path, "r") as f:
                    known_files = json.load(f)
                    for file_id, file_info in known_files.items():
                        if isinstance(file_info, dict):
                            if "last_modified" in file_info:
                                try:
                                    file_info["last_modified"] = datetime.fromisoformat(file_info["last_modified"])
                                except (ValueError, TypeError) as e:
                                    logger.warning(f"Failed to parse last_modified for {file_id}: {e}")
                    logger.info(f"Successfully loaded {len(known_files)} known files")
                    return known_files
            else:
                logger.info("No existing known_files.json found, starting with empty dictionary")
                return {}
        except Exception as e:
            logger.error(f"Error loading known files: {e}")
            return {}

    def save_known_files(self, known_files: Dict):
        """
        Save known files information to JSON file.
    
        """
        try:
            # Convert datetime objects to ISO format strings
            serializable_files = {}
            for file_id, file_info in known_files.items():
                if isinstance(file_info, dict):
                    serializable_files[file_id] = file_info.copy()
                    if "last_modified" in serializable_files[file_id]:
                        if isinstance(serializable_files[file_id]["last_modified"], datetime):
                            serializable_files[file_id]["last_modified"] = file_info["last_modified"].isoformat()
                else:
                    # Handle case where file_info is a string or other type
                    serializable_files[file_id] = file_info
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.known_files_path), exist_ok=True)
            
            with open(self.known_files_path, "w") as f:
                json.dump(serializable_files, f, indent=2)
                logger.info(f"Successfully saved {len(serializable_files)} known files")
        except Exception as e:
            logger.error(f"Error saving known files: {e}")
            raise

    async def ensure_index_exists(self):
        """
        Ensure the Elasticsearch index exists with proper mapping.
        """
        try:
            if not await self.search_provider.client.indices.exists(index="files"):
                # Create index with mapping
                await self.search_provider.client.indices.create(
                    index="files",
                    body={
                        "mappings": {
                            "properties": {
                                "path": {"type": "keyword"},
                                "content": {"type": "text"},
                                "provider": {"type": "keyword"},
                                "extension": {"type": "keyword"},
                                "last_modified": {"type": "date"}
                            }
                        }
                    }
                )
                logger.info("Created 'files' index with mapping")
        except Exception as e:
            logger.error(f"Error ensuring index exists: {e}")
            raise

    async def search_files(self, query: str) -> Dict[str, Any]:
        """
        Search for files containing the query text.
        if use_cache = True -> use local storage cache 
        if use_cache = False -> fetch files from cloud and index directly
        """
        try:
            if self.settings.USE_CACHE:
                #with local storage cache
                await self.ensure_index_exists()
                storage_service = get_storage_service(provider=self.settings.STORAGE_PROVIDER)
                known_files = self.create_load_known_files()
                await storage_service.fetch_and_index_files(known_files)
                self.save_known_files(known_files)
                await self.update_index()
            else:
                # without local storage cache
                await self.ensure_index_exists()
                storage_service = get_storage_service(provider=self.settings.STORAGE_PROVIDER)
                files = await storage_service.list_files()
                for file_info in files:
                    try:
                        content = await storage_service.get_file_content(file_info['path'])
                        if content:
                            await self.search_provider.index_file(
                                path=file_info['path'],
                                content=content,
                                provider=self.settings.STORAGE_PROVIDER,
                                extension=os.path.splitext(file_info['path'])[1],
                                last_modified=file_info.get('last_modified', datetime.now())
                            )
                    except Exception as e:
                        logger.warning(f"Failed to index file {file_info['path']}: {e}")
                        continue

            return await self.search_provider.search_files(query)
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise Exception(f"Search operation failed: {str(e)}")

    async def update_index(self):
        """
        Update the search index with latest files from the local folder.
        """
        try:
            await self.search_provider.update_index_from_local_folder()
        except Exception as e:
            logger.error(f"Index update failed: {str(e)}")
            raise Exception(f"Failed to update index: {str(e)}")

    async def close(self):
        """
        Close the search service and its connections.

        """
        await self.search_provider.close()


_search_service = None

def get_search_service() -> SearchService:
    """
    Get or create a singleton instance of SearchService.
    
    Returns:
        SearchService: The singleton instance of the search service
    """
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service