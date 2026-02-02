"""Recursive file discovery for MIDI files."""
import os
from typing import List


def scan_midi_files(
    root_dir: str,
    ignore_filename_contains: List[str] = None,
    ignore_folders: List[str] = None,
) -> List[str]:
    """Recursively scan directory for .mid and .midi files.
    
    If ignore_filename_contains is set, skip files whose basename (case-insensitive)
    contains any of the given strings.
    If ignore_folders is set, do not descend into or include files from those folder names.
    """
    if ignore_filename_contains is None:
        ignore_filename_contains = []
    if ignore_folders is None:
        ignore_folders = []
    ignore_folders_lower = [f.lower() for f in ignore_folders]
    midi_files = []
    
    for root, dirs, files in os.walk(root_dir):
        # Don't descend into ignored folders
        if ignore_folders_lower:
            dirs[:] = [d for d in dirs if d.lower() not in ignore_folders_lower]
        for file in files:
            if not file.lower().endswith(('.mid', '.midi')):
                continue
            if ignore_filename_contains:
                file_lower = file.lower()
                if any(ignore in file_lower for ignore in ignore_filename_contains):
                    continue
            full_path = os.path.join(root, file)
            midi_files.append(full_path)
    
    return sorted(midi_files)
