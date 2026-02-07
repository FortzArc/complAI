import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base application configuration
APP_CONFIG = {
    # Core settings
    'APP_NAME': 'ComplianceService',
    'DEBUG': False,
    
    # Temporary file settings
    'TEMP_DIR': Path('/tmp/compliance_checks'),
    'MAX_TEMP_FILE_AGE_HOURS': 24,
    'TEMP_FILE_PERMISSIONS': 0o644,  # rw-r--r--
    
    # Disk monitoring thresholds (percentage)
    'DISK_WARNING_THRESHOLD': 80,
    'DISK_CRITICAL_THRESHOLD': 90,
    
    # Cleanup job settings
    'CLEANUP_SCHEDULE': '0 */4 * * *',  # Every 4 hours
    'CLEANUP_ENABLED': True,
    
    # Error handling
    'MAX_CLEANUP_RETRIES': 3,
    'CLEANUP_RETRY_DELAY': 300,  # 5 minutes
}

def init_temp_directory():
    """Initialize temporary directory with correct permissions"""
    try:
        temp_dir = APP_CONFIG['TEMP_DIR']
        temp_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(temp_dir, APP_CONFIG['TEMP_FILE_PERMISSIONS'])
        logger.info(f"Initialized temp directory: {temp_dir}")
    except Exception as e:
        logger.error(f"Failed to initialize temp directory: {e}")
        raise

def get_disk_usage(path):
    """Get disk usage percentage for given path"""
    try:
        stat = os.statvfs(path)
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bfree * stat.f_frsize
        used = total - free
        return (used / total) * 100
    except Exception as e:
        logger.error(f"Failed to get disk usage: {e}")
        return None

# Initialize on module load
init_temp_directory()
