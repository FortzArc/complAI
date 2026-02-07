import os
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import psutil

logger = logging.getLogger(__name__)

# Constants
MAX_FILE_AGE_HOURS = 24
TEMP_DIR = "/tmp/compliance_pdfs"
DISK_USAGE_THRESHOLD = 85  # Percentage

class FileCleanupError(Exception):
    """Custom exception for file cleanup errors"""
    pass

def check_disk_usage():
    """
    Monitor disk usage and return True if above threshold
    """
    try:
        disk_usage = psutil.disk_usage(TEMP_DIR)
        return disk_usage.percent >= DISK_USAGE_THRESHOLD
    except Exception as e:
        logger.error(f"Failed to check disk usage: {str(e)}")
        return True

def cleanup_temp_files(force_cleanup=False):
    """
    Clean up temporary PDF files older than MAX_FILE_AGE_HOURS
    Args:
        force_cleanup (bool): If True, remove all files regardless of age
    """
    try:
        if not os.path.exists(TEMP_DIR):
            logger.info(f"Temp directory {TEMP_DIR} does not exist")
            return

        cutoff_time = datetime.now() - timedelta(hours=MAX_FILE_AGE_HOURS)
        
        # Get list of files to delete
        files_to_delete = []
        for file_path in Path(TEMP_DIR).glob("*.pdf"):
            try:
                if force_cleanup or datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_time:
                    files_to_delete.append(file_path)
            except OSError as e:
                logger.error(f"Error accessing file {file_path}: {str(e)}")
                continue

        # Delete files with error handling for each file
        for file_path in files_to_delete:
            try:
                os.chmod(file_path, 0o666)  # Ensure write permissions
                os.remove(file_path)
                logger.info(f"Deleted temp file: {file_path}")
            except OSError as e:
                logger.error(f"Failed to delete file {file_path}: {str(e)}")
                continue

        # Force cleanup if disk usage is high
        if check_disk_usage() and not force_cleanup:
            logger.warning("High disk usage detected, forcing cleanup")
            cleanup_temp_files(force_cleanup=True)

    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise FileCleanupError(f"Failed to cleanup temp files: {str(e)}")

def create_temp_file(prefix="doc_", suffix=".pdf"):
    """
    Create a temporary file with proper permissions
    """
    try:
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR, mode=0o755)
        
        temp_file = Path(TEMP_DIR) / f"{prefix}{datetime.now().strftime('%Y%m%d_%H%M%S')}{suffix}"
        temp_file.touch(mode=0o644)
        return str(temp_file)

    except Exception as e:
        logger.error(f"Failed to create temp file: {str(e)}")
        raise FileCleanupError(f"Failed to create temp file: {str(e)}")

def emergency_cleanup():
    """
    Emergency cleanup when disk space is critically low
    """
    try:
        logger.warning("Performing emergency cleanup")
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
            os.makedirs(TEMP_DIR, mode=0o755)
        logger.info("Emergency cleanup completed")
    except Exception as e:
        logger.error(f"Emergency cleanup failed: {str(e)}")
        raise FileCleanupError(f"Emergency cleanup failed: {str(e)}")
