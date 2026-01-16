"""File watcher with debounce and self-write suppression."""
import os
import time
import threading
from typing import Dict, Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent


class DebouncedHandler(FileSystemEventHandler):
    """Handler with per-file debounce and self-write suppression."""
    
    def __init__(self, callback: Callable[[str], None], debounce_seconds: float = 1.0):
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.pending: Dict[str, threading.Timer] = {}
        self.processed_files: Dict[str, tuple] = {}  # path -> (hash, mtime)
        self.lock = threading.Lock()
    
    def should_process(self, file_path: str) -> bool:
        """Check if file should be processed (suppress self-writes)."""
        from midi_io import get_file_hash, get_file_mtime
        
        with self.lock:
            current_hash = get_file_hash(file_path)
            current_mtime = get_file_mtime(file_path)
            
            if file_path in self.processed_files:
                prev_hash, prev_mtime = self.processed_files[file_path]
                # If hash unchanged and mtime is very recent (within 2 seconds), likely our write
                if current_hash == prev_hash and (current_mtime - prev_mtime) < 2.0:
                    return False
            
            # Update tracking
            self.processed_files[file_path] = (current_hash, current_mtime)
            return True
    
    def mark_processed(self, file_path: str):
        """Mark file as processed after successful write."""
        from midi_io import get_file_hash, get_file_mtime
        
        with self.lock:
            self.processed_files[file_path] = (get_file_hash(file_path), get_file_mtime(file_path))
    
    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        file_path = event.src_path
        if not file_path.lower().endswith(('.mid', '.midi')):
            return
        
        # Cancel existing timer for this file
        with self.lock:
            if file_path in self.pending:
                self.pending[file_path].cancel()
            
            # Create new timer
            timer = threading.Timer(self.debounce_seconds, self._process_file, args=(file_path,))
            self.pending[file_path] = timer
            timer.start()
    
    def on_created(self, event: FileSystemEvent):
        """Handle file creation events."""
        self.on_modified(event)
    
    def _process_file(self, file_path: str):
        """Process file after debounce delay."""
        with self.lock:
            if file_path in self.pending:
                del self.pending[file_path]
        
        if os.path.exists(file_path) and self.should_process(file_path):
            self.callback(file_path)


class Watcher:
    """File system watcher with debounce."""
    
    def __init__(self, watch_dir: str, callback: Callable[[str], None], debounce_seconds: float = 1.0):
        self.watch_dir = os.path.abspath(watch_dir)
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.observer = None
        self.handler = None
    
    def start(self):
        """Start watching for file changes."""
        self.handler = DebouncedHandler(self.callback, self.debounce_seconds)
        self.observer = Observer()
        self.observer.schedule(self.handler, self.watch_dir, recursive=True)
        self.observer.start()
        print(f"Watching {self.watch_dir} for MIDI file changes...")
    
    def stop(self):
        """Stop watching."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
    
    def mark_file_processed(self, file_path: str):
        """Mark a file as processed to suppress re-processing."""
        if self.handler:
            self.handler.mark_processed(file_path)
