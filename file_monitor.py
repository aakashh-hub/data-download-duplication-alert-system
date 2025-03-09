import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from app.hashing import generate_checksum
from app.models import FileRecord
from app import db, create_app
import tkinter as tk
from tkinter import messagebox
from collections import defaultdict
import logging
import math
from datetime import datetime

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('file_monitor.log')
    ]
)
logger = logging.getLogger(__name__)

class FileState:
    def __init__(self):
        self.size = 0
        self.last_modified = 0
        self.stable_count = 0
        self.check_count = 0
        self.initial_size = 0
        self.first_seen = datetime.now()
        self.last_size_change = datetime.now()
        self.download_speed = 0
        self.is_downloading = False

class FileTracker:
    def __init__(self):
        self.files = defaultdict(FileState)
        self.temp_file_mapping = {}  # Maps temporary files to their final names

    def update_file_state(self, file_path):
        """Update and return detailed file state information."""
        try:
            if not os.path.exists(file_path):
                return None

            state = self.files[file_path]
            current_time = datetime.now()
            current_size = os.path.getsize(file_path)
            current_modified = os.path.getmtime(file_path)

            # Initialize if this is the first check
            if state.initial_size == 0:
                state.initial_size = current_size
                state.first_seen = current_time
                logger.info(f"Initial size for {os.path.basename(file_path)}: {current_size/1024/1024:.2f} MB")

            # Calculate download speed
            time_diff = (current_time - state.last_size_change).total_seconds()
            if current_size != state.size and time_diff > 0:
                size_diff = current_size - state.size
                state.download_speed = size_diff / time_diff
                state.last_size_change = current_time
                state.is_downloading = True
                logger.info(f"Download speed for {os.path.basename(file_path)}: {state.download_speed/1024/1024:.2f} MB/s")

            # Update state
            state.size = current_size
            state.last_modified = current_modified
            state.check_count += 1

            # Log detailed status every 5 checks
            if state.check_count % 5 == 0:
                self.log_file_status(file_path, state)

            return state

        except Exception as e:
            logger.error(f"Error updating file state for {file_path}: {str(e)}")
            return None

    def log_file_status(self, file_path, state):
        """Log detailed file status information."""
        try:
            filename = os.path.basename(file_path)
            current_size_mb = state.size / 1024 / 1024
            elapsed_time = (datetime.now() - state.first_seen).total_seconds()
            
            status_msg = (
                f"\nFile Status Update for: {filename}\n"
                f"Current Size: {current_size_mb:.2f} MB\n"
                f"Download Speed: {state.download_speed/1024/1024:.2f} MB/s\n"
                f"Time Elapsed: {elapsed_time:.1f} seconds\n"
                f"Stable Count: {state.stable_count}\n"
                f"Check Count: {state.check_count}\n"
                f"Status: {'Downloading' if state.is_downloading else 'Stabilizing'}"
            )
            logger.info(status_msg)
        except Exception as e:
            logger.error(f"Error logging file status: {str(e)}")

    def is_file_ready(self, file_path):
        """Determine if a file is ready for processing with detailed checks."""
        try:
            state = self.update_file_state(file_path)
            if not state:
                return False

            # Get file extension and size
            _, ext = os.path.splitext(file_path)
            size_mb = state.size / 1024 / 1024

            # Determine required stable checks based on file type and size
            required_stable_checks = self.get_required_stable_checks(ext, size_mb)
            
            # Check if file size hasn't changed
            if state.size == state.initial_size and state.check_count > 1:
                state.stable_count += 1
            else:
                state.stable_count = 0
                state.initial_size = state.size

            # Log stability progress
            if state.stable_count > 0:
                logger.info(f"Stability progress for {os.path.basename(file_path)}: "
                          f"{state.stable_count}/{required_stable_checks}")

            # Additional checks for large files
            if size_mb > 100:  # Files larger than 100MB
                if not self.check_large_file_stability(file_path, state):
                    return False

            # Check if file is ready
            is_ready = state.stable_count >= required_stable_checks

            if is_ready:
                logger.info(f"File {os.path.basename(file_path)} is ready for processing:\n"
                          f"Final Size: {size_mb:.2f} MB\n"
                          f"Total Checks: {state.check_count}\n"
                          f"Time Taken: {(datetime.now() - state.first_seen).total_seconds():.1f} seconds")

            return is_ready

        except Exception as e:
            logger.error(f"Error checking file readiness for {file_path}: {str(e)}")
            return False

    def get_required_stable_checks(self, ext, size_mb):
        """Determine required stable checks based on file type and size."""
        # Base checks for different file types
        if ext.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
            base_checks = 3
        elif ext.lower() in ['.exe', '.msi', '.zip', '.rar']:
            base_checks = 5
        else:
            base_checks = 4

        # Adjust for file size
        if size_mb > 500:  # > 500MB
            return base_checks + 3
        elif size_mb > 100:  # > 100MB
            return base_checks + 2
        elif size_mb > 50:  # > 50MB
            return base_checks + 1
        return base_checks

    def check_large_file_stability(self, file_path, state):
        """Additional stability checks for large files."""
        try:
            # Check for reasonable download speed
            if state.is_downloading and state.download_speed < 1024:  # Less than 1 KB/s
                logger.warning(f"Download speed too low for {os.path.basename(file_path)}")
                return False

            # Check for timeout on large files
            elapsed_time = (datetime.now() - state.first_seen).total_seconds()
            if elapsed_time > 3600:  # 1 hour timeout
                logger.warning(f"Download timeout for {os.path.basename(file_path)}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error in large file stability check: {str(e)}")
            return False

    def remove_file(self, file_path):
        """Remove file from tracking."""
        if file_path in self.files:
            del self.files[file_path]
            logger.info(f"Removed {os.path.basename(file_path)} from tracking")

class FileHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app
        self.file_tracker = FileTracker()
        self.pending_files = set()

    def process_file(self, file_path):
        """Process a file once it's ready."""
        try:
            logger.info(f"Starting to process file: {os.path.basename(file_path)}")

            # Final verification
            if not os.path.exists(file_path):
                logger.warning(f"File no longer exists: {file_path}")
                return

            # Try to open the file
            try:
                with open(file_path, 'rb') as f:
                    f.read(1024)
                logger.info(f"Successfully verified file access: {os.path.basename(file_path)}")
            except Exception as e:
                logger.error(f"Cannot access file {file_path}: {str(e)}")
                return

            # Generate checksum
            logger.info(f"Generating checksum for: {os.path.basename(file_path)}")
            checksum = generate_checksum(file_path)
            if checksum is None:
                logger.error(f"Failed to generate checksum for: {file_path}")
                return

            # Database operations
            with self.app.app_context():
                existing_file = FileRecord.query.filter_by(checksum=checksum).first()
                if existing_file:
                    logger.info(f"Duplicate file detected: {file_path}")
                    self.prompt_user(file_path)
                else:
                    new_file = FileRecord(
                        checksum=checksum,
                        file_name=os.path.basename(file_path),
                        file_path=file_path,
                        file_size=os.path.getsize(file_path),
                        file_type=os.path.splitext(file_path)[1]
                    )
                    db.session.add(new_file)
                    db.session.commit()
                    logger.info(f"Successfully added to database: {file_path}")

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
        finally:
            self.cleanup_file(file_path)

    def cleanup_file(self, file_path):
        """Clean up tracking for a file."""
        self.file_tracker.remove_file(file_path)
        self.pending_files.discard(file_path)
        logger.info(f"Completed processing for: {os.path.basename(file_path)}")

    def check_pending_files(self):
        """Check if any pending files are ready for processing."""
        for file_path in list(self.pending_files):
            try:
                if not os.path.exists(file_path):
                    logger.info(f"Pending file no longer exists: {file_path}")
                    self.cleanup_file(file_path)
                    continue

                if self.file_tracker.is_file_ready(file_path):
                    logger.info(f"File ready for processing: {file_path}")
                    self.process_file(file_path)

            except Exception as e:
                logger.error(f"Error checking pending file {file_path}: {str(e)}")

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        logger.info(f"New file detected: {file_path}")

        # Handle temporary files
        if any(file_path.endswith(ext) for ext in ['.crdownload', '.tmp', '.part']):
            logger.info(f"Monitoring temporary file: {file_path}")
            return

        # Add to pending files
        self.pending_files.add(file_path)
        logger.info(f"Added to pending files: {os.path.basename(file_path)}")

    def prompt_user(self, file_path):
        def on_keep():
            root.destroy()
            logger.info(f"User chose to keep duplicate file: {file_path}")

        def on_delete():
            try:
                os.remove(file_path)
                logger.info(f"User chose to delete duplicate file: {file_path}")
            except Exception as e:
                logger.error(f"Error deleting file: {e}")
            root.destroy()

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        result = messagebox.askquestion("Duplicate File Detected",
                                      f"Duplicate file detected: {os.path.basename(file_path)}\n"
                                      "Do you want to keep it or delete it?",
                                      icon='warning')
        if result == 'yes':
            on_keep()
        else:
            on_delete()

def start_observer():
    app = create_app()
    path_to_watch = r"C:\Users\aakas\Downloads"
    event_handler = FileHandler(app)
    observer = Observer()
    observer.schedule(event_handler, path=path_to_watch, recursive=False)
    observer.start()

    logger.info(f"Started file monitoring in: {path_to_watch}")
    logger.info("Monitoring configuration:")
    logger.info(f"- Path: {path_to_watch}")
    logger.info("- Monitoring for all file types")
    logger.info("- Detailed logging enabled")

    try:
        while True:
            event_handler.check_pending_files()
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("File monitoring stopped by user")
    observer.join()

if __name__ == "__main__":
    start_observer()