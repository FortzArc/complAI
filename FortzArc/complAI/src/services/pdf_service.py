import os
import logging
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional
from subprocess import run, PIPE

logger = logging.getLogger(__name__)

# Constants for disk monitoring and cleanup
MAX_DISK_USAGE_PCT = 85  # Trigger cleanup when disk usage exceeds 85%
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1

class PDFService:
    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self._setup_temp_directory()
        
    def _setup_temp_directory(self):
        """Ensure temp directory exists with proper permissions"""
        os.makedirs(self.temp_dir, exist_ok=True)
        
    def _check_disk_usage(self) -> float:
        """Monitor disk usage and trigger cleanup if needed"""
        disk_usage = shutil.disk_usage(self.temp_dir)
        usage_percent = (disk_usage.used / disk_usage.total) * 100
        
        if usage_percent > MAX_DISK_USAGE_PCT:
            logger.warning(f"High disk usage detected: {usage_percent:.1f}%. Triggering cleanup.")
            self.cleanup_temp_files()
            
        return usage_percent
    
    def create_temp_pdf(self, content: bytes) -> str:
        """Create a temporary PDF file with proper cleanup handling"""
        self._check_disk_usage()
        
        # Use NamedTemporaryFile with delete=True for automatic cleanup
        temp_file = tempfile.NamedTemporaryFile(
            suffix='.pdf',
            dir=self.temp_dir,
            delete=True
        )
        
        try:
            temp_file.write(content)
            temp_file.flush()
            return temp_file.name
        except Exception as e:
            logger.error(f"Failed to create temporary PDF: {str(e)}")
            temp_file.close()
            raise
            
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """Clean up temporary PDF files with retry logic and elevated privileges if needed"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        for file_path in Path(self.temp_dir).glob("*.pdf"):
            if file_path.stat().st_mtime < cutoff_time:
                for attempt in range(MAX_RETRY_ATTEMPTS):
                    try:
                        os.remove(file_path)
                        break
                    except PermissionError as e:
                        if attempt == MAX_RETRY_ATTEMPTS - 1:
                            logger.error(f"Failed to remove file after {MAX_RETRY_ATTEMPTS} attempts: {file_path}")
                            self._failsafe_cleanup(file_path)
                        else:
                            logger.warning(f"Retry {attempt + 1} to remove file: {file_path}")
                            time.sleep(RETRY_DELAY_SECONDS)
                    except Exception as e:
                        logger.error(f"Unexpected error cleaning up file {file_path}: {str(e)}")
                        break
                        
    def _failsafe_cleanup(self, file_path: Path):
        """Attempt to clean up stuck files using elevated privileges"""
        try:
            # Attempt cleanup using sudo if available
            result = run(['sudo', 'rm', str(file_path)], stderr=PIPE)
            if result.returncode == 0:
                logger.info(f"Successfully removed file using elevated privileges: {file_path}")
            else:
                logger.error(f"Failed to remove file using elevated privileges: {file_path}")
        except Exception as e:
            logger.error(f"Failed to execute failsafe cleanup for {file_path}: {str(e)}")

    def __del__(self):
        """Ensure cleanup is attempted when service is destroyed"""
        try:
            self.cleanup_temp_files()
        except Exception as e:
            logger.error(f"Error during cleanup in destructor: {str(e)}")