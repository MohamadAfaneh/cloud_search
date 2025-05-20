from typing import List, Optional
from datetime import datetime
import logging
import os
import json
import dropbox
from dropbox.files import FileMetadata
from ..core.config import get_settings

logger = logging.getLogger(__name__)

class CloudStorageService():
    """
    Base class for cloud storage services.
    """
    
    def __init__(self, provider: str):
        """
        Initialize the cloud storage service.
        
        """
        self.provider = provider
        self.settings = get_settings()
        self.download_folder = self.settings.DOWNLOAD_FOLDER
        self.known_files_path = self.settings.KNOWN_FILES_PATH
        logger.info(f"Initializing storage service for provider: {provider}")

class DropBoxStorage(CloudStorageService):
    """
    Dropbox implementation of the cloud storage service.
    """
    
    def __init__(self):
        """
        Initialize the Dropbox storage service.
        """
        super().__init__("dropbox")
        if not self.settings.DROPBOX_ACCESS_TOKEN:
            logger.warning("DROPBOX_ACCESS_TOKEN not set. Some functionality will be limited.")
            self.client = None
        else:
            self.client = dropbox.Dropbox(self.settings.DROPBOX_ACCESS_TOKEN)
            logger.info("Initialized Dropbox client")

    async def list_files(self) -> List[dict]:
        """
        List all files in the Dropbox account.
        """
        if not self.client:
            logger.error("Cannot list files")
            return []
            
        try:
            result = self.client.files_list_folder('', recursive=True)
            files = []

            while True:
                for entry in result.entries:
                    if isinstance(entry, FileMetadata):
                        files.append({
                            'path': entry.path_lower,
                            'last_modified': entry.client_modified
                        })

                if result.has_more:
                    result = self.client.files_list_folder_continue(result.cursor)
                else:
                    break

            return files
            
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            raise

    async def get_file_content(self, path: str) -> Optional[bytes]:
        """
        Get the content of a file from Dropbox.

        """
        if not self.client:
            logger.error("Cannot get file content: Dropbox client not initialized (missing access token)")
            return None
            
        try:
            metadata, res = self.client.files_download(path)
            return res.content
        except Exception as e:
            logger.error(f"Error getting file content for {path}: {str(e)}")
            return None

    async def fetch_and_index_files(self, known_files):
        """
        Fetch and index files from Dropbox.
        """
        if not self.client:
            logger.error("Cannot fetch files: Dropbox client not initialized (missing access token)")
            return
            
        try:
            result = self.client.files_list_folder('', recursive=True)
            current_files = set()
            downloaded_files = set()  # Track files we've already downloaded in this session

            while True:
                for entry in result.entries:
                    if isinstance(entry, FileMetadata):
                        path = entry.path_lower
                        current_files.add(path)
                        last_modified = entry.client_modified

                        # Skip if we've already downloaded this file in this session
                        if path in downloaded_files:
                            logger.debug(f"Skipping already downloaded file: {path}")
                            continue

                        if path not in known_files or known_files[path] < last_modified.isoformat():
                            logger.info(f"New or updated file detected: {path}")
                            try:
                                await self.download_file(path, last_modified)
                                downloaded_files.add(path)  # Mark as downloaded
                                known_files[path] = last_modified.isoformat()
                            except Exception as e:
                                logger.error(f"Failed to download file {path}: {str(e)}")
                                continue
                        else:
                            logger.debug(f"No changes detected for: {path}")

                if result.has_more:
                    result = self.client.files_list_folder_continue(result.cursor)
                else:
                    break

            # Handle removed files
            removed_files = set(known_files.keys()) - current_files
            for deleted_path in removed_files:
                logger.info(f"File deleted from cloud, removing: {deleted_path}")
        
                #local cache path
                local_path = os.path.join(self.download_folder, deleted_path.lstrip("/"))
        
                # Delete from local cache if it exists
                if os.path.exists(local_path):
                    os.remove(local_path)
                    logger.info(f"Deleted local file: {local_path}")
        
                # Remove from known_files
                del known_files[deleted_path]

            # Save updated known_files to JSON
            os.makedirs(os.path.dirname(self.known_files_path), exist_ok=True)
            with open(self.known_files_path, "w") as f:
                json.dump(known_files, f, indent=2)

        except Exception as e:
            logger.error(f"Error in fetch_and_index_files: {str(e)}")
            raise

    async def download_file(self, path: str, last_modified: datetime):
        """
        Download a file from Dropbox to local storage.
        """
        if not self.client:
            logger.error("Cannot download file")
            return
            
        try:
            logger.info(f"Starting download of file: {path}")
            metadata, res = self.client.files_download(path)
            content = res.content
            local_path = os.path.join(self.download_folder, path.lstrip("/"))
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            #write to local cache
            with open(local_path, "wb") as f:
                f.write(content)
            logger.info(f"Successfully saved file to: {local_path}")
            
            # Verify file was written correctly
            if os.path.exists(local_path):
                file_size = os.path.getsize(local_path)
                logger.info(f"Verified file size: {file_size} bytes")
            else:
                logger.error(f"File was not written correctly: {local_path}")
            
        except Exception as e:
            logger.error(f"Error downloading file {path}: {str(e)}")
            raise

s_service =None

def get_storage_service(provider: str) -> CloudStorageService:
    """
    Factory function to get the appropriate storage service based on provider name.
    """
    global s_service
    logger.debug(f"Getting storage service for provider: {provider}")
    if provider == "dropbox":
        s_service = DropBoxStorage()
    else:
        raise ValueError(f"Unsupported storage provider: {provider}")
    return s_service