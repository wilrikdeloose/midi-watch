"""MIDI file I/O with retry logic and atomic writes."""
import os
import time
import hashlib
from typing import Optional, Tuple
import mido


def read_midi_with_retry(file_path: str, max_retries: int = 5, retry_delay: float = 0.1) -> Optional[mido.MidiFile]:
    """Read MIDI file with retry logic for partial writes."""
    for attempt in range(max_retries):
        try:
            midi = mido.MidiFile(file_path)
            # Try to access tracks to ensure file is fully readable
            _ = len(midi.tracks)
            return midi
        except (OSError, IOError, ValueError) as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                print(f"Error reading {file_path} after {max_retries} attempts: {e}")
                return None
    return None


def write_midi_atomic(midi: mido.MidiFile, file_path: str) -> bool:
    """Write MIDI file atomically using temp file and os.replace."""
    try:
        # Create temp file in same directory
        dir_path = os.path.dirname(os.path.abspath(file_path))
        temp_path = os.path.join(dir_path, f".{os.path.basename(file_path)}.tmp")
        
        midi.save(temp_path)
        os.replace(temp_path, file_path)
        return True
    except Exception as e:
        print(f"Error writing {file_path}: {e}")
        # Clean up temp file if it exists
        temp_path = os.path.join(os.path.dirname(os.path.abspath(file_path)), 
                                 f".{os.path.basename(file_path)}.tmp")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return False


def get_file_hash(file_path: str) -> Optional[str]:
    """Get SHA256 hash of file contents."""
    try:
        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return None


def get_file_mtime(file_path: str) -> float:
    """Get file modification time."""
    try:
        return os.path.getmtime(file_path)
    except Exception:
        return 0.0
