import os
import tempfile
import logging
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class PDFGenerator:
    def __init__(self, temp_dir: Optional[str] = None):
        # Use system temp dir if none specified, ensure it exists
        self.temp_dir = temp_dir or tempfile.gettempdir()
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Set restrictive but sufficient permissions on temp dir
        os.chmod(self.temp_dir, 0o755)

    def generate_pdf(self, content: str) -> str:
        """Generate PDF and return path to temporary file"""
        try:
            # Create temp file with proper permissions
            temp_file = tempfile.NamedTemporaryFile(
                suffix='.pdf',
                dir=self.temp_dir,
                delete=False,
                mode='w+b'
            )
            
            # Set file permissions to be readable/writable by service
            os.chmod(temp_file.name, 0o644)
            
            # Write PDF content
            # ... PDF generation logic here ...
            
            return temp_file.name

        except (IOError, OSError) as e:
            logger.error(f"Failed to generate PDF: {str(e)}")
            self._cleanup_temp_file(temp_file.name)
            raise

    def cleanup_old_files(self, max_age_hours: int = 24):
        """Clean up temporary PDF files older than specified hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            for file_path in Path(self.temp_dir).glob('*.pdf'):
                try:
                    # Check file age
                    mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if mtime < cutoff_time:
                        self._cleanup_temp_file(str(file_path))
                        
                except (OSError, IOError) as e:
                    # Log but continue if single file cleanup fails
                    logger.error(f"Failed to check/remove file {file_path}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Failed to run cleanup job: {str(e)}")
            raise

    def _cleanup_temp_file(self, file_path: str) -> None:
        """Safely remove a temporary file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up temp file: {file_path}")
                
        except (OSError, IOError) as e:
            logger.error(f"Failed to remove temp file {file_path}: {str(e)}")
            raise

    def __del__(self):
        """Attempt cleanup on object destruction"""
        try:
            self.cleanup_old_files()
        except Exception as e:
            logger.error(f"Failed cleanup during destruction: {str(e)}")
