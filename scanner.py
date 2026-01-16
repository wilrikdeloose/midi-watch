"""Recursive file discovery for MIDI files."""
import os
from typing import List


def scan_midi_files(root_dir: str) -> List[str]:
    """Recursively scan directory for .mid and .midi files."""
    midi_files = []
    
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(('.mid', '.midi')):
                full_path = os.path.join(root, file)
                midi_files.append(full_path)
    
    return sorted(midi_files)
