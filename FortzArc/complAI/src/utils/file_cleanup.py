import os
import logging
import shutil
import tempfile
import time
from pathlib import Path
from typing import List, Optional
import psutil
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
DISK_USAGE_THRESHOLD = 90  # percentage
TEMP_DIR = tempfile.gettempdir()

class FileCleanupManager:
    def __init__(self, directory: str = TEMP_DIR):
        self.directory = directory
        self.cleanup_patterns = ['*.pdf', '*.tmp']
    
    def check_disk_usage(self) -> float:
        """Monitor disk usage and return usage percentage."""
        disk_usage = psutil.disk_usage(self.directory)
        usage_percent = disk_usage.percent
        if usage_percent > DISK_USAGE_THRESHOLD:
            logger.warning(f"High disk usage detected: {usage_percent}%")
        return usage_percent

    def create_temp_file(self, suffix: str = '.pdf') -> tempfile.NamedTemporaryFile:
        """Create a temporary file that will be automatically deleted on close."""
        return tempfile.NamedTemporaryFile(suffix=suffix, delete=True)

    def cleanup_files(self, max_age_hours: int = 24) -> None:
        """Clean up temporary files with proper error handling and retries."""
        try:
            if self.check_disk_usage() > DISK_USAGE_THRESHOLD:
                logger.info("Initiating emergency cleanup due to high disk usage")
                max_age_hours = 1  # More aggressive cleanup
            
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for pattern in self.cleanup_patterns:
                for filepath in Path(self.directory).glob(pattern):
                    try:
                        if (current_time - filepath.stat().st_mtime) > max_age_seconds:
                            self._remove_file_with_retry(filepath)
                    except Exception as e:
                        logger.error(f"Error processing file {filepath}: {str(e)}")

        except Exception as e:
            logger.error(f"Cleanup operation failed: {str(e)}")
            
    def _remove_file_with_retry(self, filepath: Path) -> None:
        """Attempt to remove a file with retries and escalating privileges if needed."""
        for attempt in range(MAX_RETRIES):
            try:
                filepath.unlink()
                logger.info(f"Successfully removed file: {filepath}")
                return
            except PermissionError:
                logger.warning(f"Permission error removing {filepath}, attempt {attempt + 1}/{MAX_RETRIES}")
                if attempt == MAX_RETRIES - 1:
                    self._force_remove_with_sudo(filepath)
                else:
                    time.sleep(RETRY_DELAY)
            except FileNotFoundError:
                logger.info(f"File already removed: {filepath}")
                return
            except Exception as e:
                logger.error(f"Unexpected error removing {filepath}: {str(e)}")
                if attempt == MAX_RETRIES - 1:
                    raise

    def _force_remove_with_sudo(self, filepath: Path) -> None:
        """Use sudo to force remove a file when normal deletion fails."""
        try:
            logger.warning(f"Attempting privileged removal of {filepath}")
            subprocess.run(['sudo', 'rm', '-f', str(filepath)], check=True)
            logger.info(f"Successfully removed file with elevated privileges: {filepath}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to remove file even with sudo: {filepath}, error: {str(e)}")
            raise

    def emergency_cleanup(self) -> None:
        """Perform emergency cleanup when disk usage is critical."""
        logger.warning("Initiating emergency cleanup procedure")
        self.cleanup_files(max_age_hours=1)
        if self.check_disk_usage() > DISK_USAGE_THRESHOLD:
            logger.error("Disk usage still critical after emergency cleanup")

def get_temp_filepath(suffix: str = '.pdf') -> str:
    """Get a temporary file path that will be automatically cleaned up."""
    temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=True)
    return temp_file.name

# Initialize global cleanup manager
cleanup_manager = FileCleanupManager()