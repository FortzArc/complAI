import os
import tempfile
import logging
import shutil
import psutil
import time
from pathlib import Path
from typing import Optional
from subprocess import run, PIPE

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TempFileManager:
    def __init__(self, 
                 base_dir: Optional[str] = None,
                 max_disk_usage_percent: float = 90.0,
                 cleanup_threshold_percent: float = 85.0,
                 max_retries: int = 3,
                 retry_delay: float = 1.0):
        
        self.base_dir = base_dir or tempfile.gettempdir()
        self.max_disk_usage = max_disk_usage_percent
        self.cleanup_threshold = cleanup_threshold_percent
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Ensure base directory exists and has proper permissions
        os.makedirs(self.base_dir, exist_ok=True)
        
    def create_temp_file(self, suffix: str = '.pdf') -> tempfile.NamedTemporaryFile:
        """Create a temporary file that will be automatically deleted when closed"""
        # Use delete=True to ensure automatic cleanup
        return tempfile.NamedTemporaryFile(
            suffix=suffix,
            dir=self.base_dir,
            delete=True
        )
    
    def check_disk_usage(self) -> float:
        """Check current disk usage percentage"""
        disk_usage = psutil.disk_usage(self.base_dir)
        return disk_usage.percent
    
    def emergency_cleanup(self):
        """Perform emergency cleanup with elevated privileges if needed"""
        logger.warning("Attempting emergency cleanup with elevated privileges")
        try:
            # Use sudo to force remove stuck files
            cmd = ['sudo', 'rm', '-rf', os.path.join(self.base_dir, '*.pdf')]
            result = run(cmd, stdout=PIPE, stderr=PIPE)
            if result.returncode == 0:
                logger.info("Emergency cleanup successful")
            else:
                logger.error(f"Emergency cleanup failed: {result.stderr.decode()}")
        except Exception as e:
            logger.error(f"Emergency cleanup failed: {str(e)}")
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """Clean up old temporary files with retry logic"""
        current_time = time.time()
        
        # Check disk usage first
        if self.check_disk_usage() > self.cleanup_threshold:
            logger.warning("Disk usage above threshold, initiating cleanup")
            
            for root, _, files in os.walk(self.base_dir):
                for filename in files:
                    if filename.endswith('.pdf'):
                        file_path = Path(root) / filename
                        
                        # Check file age
                        try:
                            file_age = current_time - os.path.getctime(file_path)
                            if file_age > (max_age_hours * 3600):
                                
                                # Attempt file removal with retries
                                for attempt in range(self.max_retries):
                                    try:
                                        file_path.unlink()
                                        logger.info(f"Successfully removed: {file_path}")
                                        break
                                    except PermissionError as e:
                                        logger.warning(f"Permission error removing {file_path} (attempt {attempt + 1}): {str(e)}")
                                        if attempt == self.max_retries - 1:
                                            # If all retries failed, try emergency cleanup
                                            self.emergency_cleanup()
                                        else:
                                            time.sleep(self.retry_delay)
                                    except Exception as e:
                                        logger.error(f"Error removing {file_path}: {str(e)}")
                                        break
                                        
                        except Exception as e:
                            logger.error(f"Error checking file age for {file_path}: {str(e)}")
        
        # Check final disk usage
        final_usage = self.check_disk_usage()
        if final_usage > self.max_disk_usage:
            logger.critical(f"Disk usage still critical after cleanup: {final_usage}%")
            self.emergency_cleanup()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_old_files()

# Default instance
temp_file_manager = TempFileManager()