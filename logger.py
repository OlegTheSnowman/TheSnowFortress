import logging
import os
import sys

def setup_logger():
    """Sets up a logger that writes to a file and the console."""

    # Determine the correct path for the log file
    if getattr(sys, 'frozen', False):
        # The application is running as a bundled exe
        app_dir = os.path.dirname(sys.executable)
    else:
        # The application is running as a script
        app_dir = os.path.dirname(os.path.abspath(__file__))

    log_file_path = os.path.join(app_dir, 'log.log')

    # Configure the logger
    log = logging.getLogger('SoundpackUpdater')
    log.setLevel(logging.DEBUG) # Capture all levels of messages

    # Prevent adding multiple handlers if this function is called more than once
    if log.hasHandlers():
        log.handlers.clear()

    # Create a file handler to write detailed logs to log.log
    try:
        file_handler = logging.FileHandler(log_file_path, mode='w') # 'w' overwrites the log on each run
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s')
        file_handler.setFormatter(formatter)
        log.addHandler(file_handler)
    except (IOError, PermissionError) as e:
        # If we can't write to the file, we can't do much, but we should know.
        print(f"FATAL: Could not open log file at {log_file_path}. Error: {e}")

    return log

# Create a single logger instance to be used by all other modules
log = setup_logger()