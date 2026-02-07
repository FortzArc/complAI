#!/usr/bin/env python3
import os
import psutil
import logging
from typing import Dict, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DiskMonitor:
    def __init__(self, warning_threshold: int = 80, critical_threshold: int = 90):
        """
        Initialize disk monitor with configurable thresholds
        warning_threshold: Percentage at which to emit warning
        critical_threshold: Percentage at which to emit critical alert
        """
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.temp_dirs = ['/tmp', '/var/tmp']  # Directories to monitor

    def check_disk_usage(self, path: str = '/') -> Dict[str, float]:
        """
        Check disk usage for given path
        Returns dict with usage metrics
        """
        try:
            disk_usage = psutil.disk_usage(path)
            return {
                'total': disk_usage.total,
                'used': disk_usage.used,
                'free': disk_usage.free,
                'percent': disk_usage.percent
            }
        except Exception as e:
            logger.error(f"Failed to check disk usage for {path}: {str(e)}")
            return {}

    def cleanup_temp_files(self, max_age_hours: int = 24) -> None:
        """
        Clean up old temporary files
        max_age_hours: Maximum age of files to keep
        """
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)

        for temp_dir in self.temp_dirs:
            try:
                if not os.path.exists(temp_dir):
                    continue

                for filename in os.listdir(temp_dir):
                    filepath = os.path.join(temp_dir, filename)
                    try:
                        # Skip if not a file or if recently modified
                        if not os.path.isfile(filepath):
                            continue
                        
                        stats = os.stat(filepath)
                        if stats.st_mtime > cutoff_time:
                            continue

                        # Remove old temp files
                        os.remove(filepath)
                        logger.info(f"Cleaned up old temp file: {filepath}")

                    except (OSError, PermissionError) as e:
                        logger.error(f"Failed to process {filepath}: {str(e)}")

            except Exception as e:
                logger.error(f"Failed to cleanup directory {temp_dir}: {str(e)}")

    def monitor(self) -> Optional[Dict]:
        """
        Main monitoring function that checks disk usage and triggers cleanup
        Returns monitoring metrics or None on failure
        """
        try:
            metrics = {}
            
            # Check each temp directory
            for temp_dir in self.temp_dirs:
                usage = self.check_disk_usage(temp_dir)
                if usage:
                    metrics[temp_dir] = usage
                    
                    # Trigger cleanup if usage exceeds warning threshold
                    if usage['percent'] >= self.warning_threshold:
                        logger.warning(f"High disk usage ({usage['percent']}%) in {temp_dir}")
                        self.cleanup_temp_files()
                        
                    # Emit critical alert if usage exceeds critical threshold    
                    if usage['percent'] >= self.critical_threshold:
                        logger.critical(f"Critical disk usage ({usage['percent']}%) in {temp_dir}")

            # Check root filesystem
            root_usage = self.check_disk_usage('/')
            if root_usage:
                metrics['/'] = root_usage

            return metrics

        except Exception as e:
            logger.error(f"Monitoring failed: {str(e)}")
            return None

    def set_correct_permissions(self, path: str, mode: int = 0o755) -> None:
        """
        Set correct permissions on directory and its contents
        """
        try:
            os.chmod(path, mode)
            logger.info(f"Set permissions {oct(mode)} on {path}")
        except Exception as e:
            logger.error(f"Failed to set permissions on {path}: {str(e)}")

if __name__ == '__main__':
    monitor = DiskMonitor()
    monitor.monitor()
