"""Main entry point for MIDI watcher/transformer."""
import os
import sys
import time
from config_loader import load_config
from scanner import scan_midi_files
from watcher import Watcher
from midi_io import read_midi_with_retry, write_midi_atomic, get_file_hash
from pipeline import process_midi


def process_file(file_path: str, config, watcher=None) -> bool:
    """Process a single MIDI file. Returns True if file was modified."""
    try:
        # Read MIDI file
        midi = read_midi_with_retry(file_path)
        if midi is None:
            print(f"  Skipped {file_path} (read failed)")
            return False
        
        # Get original hash
        original_hash = get_file_hash(file_path)
        
        # Process MIDI
        processed_midi = process_midi(midi, file_path, config)
        
        # Check if content changed by comparing hashes
        # Write to temp file in system temp directory (not in workspace)
        import tempfile
        temp_dir = tempfile.gettempdir()
        
        # Get temp file path and ensure it's closed before using it
        with tempfile.NamedTemporaryFile(dir=temp_dir, delete=False, suffix='.mid', prefix='midi-watch_') as tmp:
            tmp_path = tmp.name
        
        import time
        try:
            # Save MIDI to temp file (this will open/close the file itself)
            processed_midi.save(tmp_path)
            
            # Ensure file is fully written and closed (Windows may need a moment)
            time.sleep(0.01)  # Small delay for Windows file system
            
            new_hash = get_file_hash(tmp_path)
            
            if new_hash == original_hash:
                os.remove(tmp_path)
                print(f"  Skipped {file_path} (no changes)")
                return False
            
            # Atomic replace - retry on Windows if needed
            max_replace_retries = 3
            for attempt in range(max_replace_retries):
                try:
                    os.replace(tmp_path, file_path)
                    print(f"  Processed {file_path}")
                    if watcher:
                        watcher.mark_file_processed(file_path)
                    return True
                except OSError as e:
                    if attempt < max_replace_retries - 1:
                        time.sleep(0.1)  # Wait a bit and retry
                    else:
                        print(f"  Failed to write {file_path}: {e}")
                        return False
        except Exception as e:
            print(f"  Error processing {file_path}: {e}")
            return False
        finally:
            # Clean up temp file only if replace didn't succeed
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass
        
    except Exception as e:
        print(f"  Error processing {file_path}: {e}")
        return False


def main():
    """Main entry point."""
    # Load configuration
    try:
        config = load_config()
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Get current working directory
    work_dir = os.getcwd()
    print(f"MIDI Watcher/Transformer")
    print(f"Working directory: {work_dir}")
    print()
    
    # Initial scan and process
    print("Scanning for MIDI files...")
    midi_files = scan_midi_files(work_dir)
    print(f"Found {len(midi_files)} MIDI file(s)")
    print()
    
    if midi_files:
        print("Processing files...")
        processed_count = 0
        skipped_count = 0
        
        for file_path in midi_files:
            if process_file(file_path, config):
                processed_count += 1
            else:
                skipped_count += 1
        
        print()
        print(f"Initial scan complete: {processed_count} processed, {skipped_count} skipped")
        print()
    
    # Start watcher
    watcher = Watcher(work_dir, lambda path: process_file(path, config, watcher), debounce_seconds=1.0)
    watcher.start()
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        watcher.stop()
        print("Exiting.")


if __name__ == "__main__":
    main()
