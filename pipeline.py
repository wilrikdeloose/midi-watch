"""Pipeline to orchestrate MIDI transformations based on config and filename."""
import os
from typing import Optional
import mido
from config_loader import Config
from transformers import (
    strip_to_notes,
    transpose_notes,
    cap_note_lengths,
    force_channel_zero,
    set_track_names,
)


def process_midi(midi: mido.MidiFile, file_path: str, config: Config) -> mido.MidiFile:
    """Apply all transformations to MIDI file based on config and filename."""
    filename_lower = os.path.basename(file_path).lower()
    
    # 1. Global: Strip to notes (preserve timing), optionally keep meta (e.g. set_tempo)
    if config.global_.strip_to_notes:
        midi = strip_to_notes(midi, keep_meta_subtypes=config.global_.strip_keep_meta)
    
    # 2. Check for specific filename rules
    bass_match = any(keyword in filename_lower for keyword in config.rules.bass.filename_contains)
    drums_match = any(keyword in filename_lower for keyword in config.rules.drums.filename_contains)
    
    # 3. Filename rule: Bass transposition
    if bass_match:
        midi = transpose_notes(midi, config.rules.bass.transpose_semitones)
        # Set track name if configured
        if config.rules.bass.track_name:
            midi = set_track_names(midi, config.rules.bass.track_name)
    
    # 4. Filename rule: Drums note length cap
    if drums_match:
        midi = cap_note_lengths(midi, config.rules.drums.max_note_length)
        # Set track name if configured
        if config.rules.drums.track_name:
            midi = set_track_names(midi, config.rules.drums.track_name)
    
    # 5. Wildcard rule: Apply if no other rules matched
    if not bass_match and not drums_match and config.rules.wildcard:
        if config.rules.wildcard.transpose_semitones is not None:
            midi = transpose_notes(midi, config.rules.wildcard.transpose_semitones)
        if config.rules.wildcard.track_name:
            midi = set_track_names(midi, config.rules.wildcard.track_name)
        if config.rules.wildcard.max_note_length:
            midi = cap_note_lengths(midi, config.rules.wildcard.max_note_length)
    
    # 6. Global: Force channel zero
    if config.global_.force_channel_zero:
        midi = force_channel_zero(midi)
    
    return midi
