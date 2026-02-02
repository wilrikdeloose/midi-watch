"""Pure MIDI transformation functions."""
from typing import List, Dict, Tuple, Optional
import mido


def strip_to_notes(midi: mido.MidiFile, keep_meta_subtypes: List[str] = None) -> mido.MidiFile:
    """Strip all events except notes, end_of_track, and optionally other meta types (e.g. set_tempo)."""
    if keep_meta_subtypes is None:
        keep_meta_subtypes = []
    new_tracks = []
    
    for track in midi.tracks:
        new_track = mido.MidiTrack()
        accumulated_time = 0
        
        for msg in track:
            accumulated_time += msg.time
            
            keep = False
            if msg.type in ('note_on', 'note_off'):
                keep = True
            elif msg.type == 'end_of_track' or msg.type in keep_meta_subtypes:
                # In mido, meta messages use .type for the specific type (set_tempo, end_of_track), not 'meta_message'
                keep = True
            
            if keep:
                if msg.type in ('note_on', 'note_off'):
                    new_msg = mido.Message(
                        msg.type,
                        channel=msg.channel,
                        note=msg.note,
                        velocity=msg.velocity,
                        time=accumulated_time
                    )
                    new_track.append(new_msg)
                else:
                    new_msg = msg.copy(time=accumulated_time)
                    new_track.append(new_msg)
                accumulated_time = 0
        
        new_tracks.append(new_track)
    
    new_midi = mido.MidiFile(ticks_per_beat=midi.ticks_per_beat)
    new_midi.tracks = new_tracks
    return new_midi


def transpose_notes(midi: mido.MidiFile, semitones: int) -> mido.MidiFile:
    """Transpose all notes by semitones, clamping to 0-127."""
    new_tracks = []
    
    for track in midi.tracks:
        new_track = mido.MidiTrack()
        for msg in track:
            if msg.type in ('note_on', 'note_off'):
                new_note = max(0, min(127, msg.note + semitones))
                new_msg = mido.Message(
                    msg.type,
                    channel=msg.channel,
                    note=new_note,
                    velocity=msg.velocity,
                    time=msg.time
                )
                new_track.append(new_msg)
            else:
                new_track.append(msg)
        new_tracks.append(new_track)
    
    new_midi = mido.MidiFile(ticks_per_beat=midi.ticks_per_beat)
    new_midi.tracks = new_tracks
    return new_midi


def cap_note_lengths(midi: mido.MidiFile, max_note_fraction: str) -> mido.MidiFile:
    """Cap note lengths to maximum (e.g., '1/8' = eighth note)."""
    # Parse fraction (only support "1/8" for now)
    if max_note_fraction != "1/8":
        raise ValueError(f"Unsupported max_note fraction: {max_note_fraction}")
    
    max_len_ticks = midi.ticks_per_beat // 2  # 1/8 note = half a beat
    
    new_tracks = []
    
    for track in midi.tracks:
        # Convert to absolute time with original index for stable sorting
        abs_events: List[Tuple[int, int, mido.Message]] = []  # (abs_time, orig_idx, msg)
        current_time = 0
        
        for idx, msg in enumerate(track):
            current_time += msg.time
            abs_events.append((current_time, idx, msg))
        
        # Match note_on/note_off pairs using stack per (note, channel) for overlapping notes
        note_stacks: Dict[Tuple[int, int], List[int]] = {}  # (note, channel) -> [on_abs_times]
        note_pairs: Dict[Tuple[int, int, int], int] = {}  # (note, channel, on_time) -> off_time
        note_off_to_on: Dict[Tuple[int, int], int] = {}  # (abs_time, orig_idx) of note_off -> on_time
        
        for abs_time, orig_idx, msg in abs_events:
            if msg.type == 'note_on' and msg.velocity > 0:
                key = (msg.note, msg.channel)
                if key not in note_stacks:
                    note_stacks[key] = []
                note_stacks[key].append(abs_time)
                note_pairs[(msg.note, msg.channel, abs_time)] = None  # Will be set by note_off
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                key = (msg.note, msg.channel)
                if key in note_stacks and note_stacks[key]:
                    on_time = note_stacks[key].pop()
                    note_pairs[(msg.note, msg.channel, on_time)] = abs_time
                    note_off_to_on[(abs_time, orig_idx)] = on_time
        
        # Cap note lengths
        for (note, channel, on_time), off_time in note_pairs.items():
            if off_time is not None:
                length = off_time - on_time
                if length > max_len_ticks:
                    note_pairs[(note, channel, on_time)] = on_time + max_len_ticks
        
        # Rebuild events: replace note_offs with adjusted times, keep everything else
        adjusted_events: List[Tuple[int, int, mido.Message]] = []
        
        for abs_time, orig_idx, msg in abs_events:
            if msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                # Check if this note_off was matched to a note_on
                if (abs_time, orig_idx) in note_off_to_on:
                    on_time = note_off_to_on[(abs_time, orig_idx)]
                    new_off_time = note_pairs.get((msg.note, msg.channel, on_time), abs_time)
                    if new_off_time != abs_time:
                        # Replace with adjusted note_off at new time
                        new_msg = mido.Message('note_off', channel=msg.channel, note=msg.note, velocity=0, time=0)
                        adjusted_events.append((new_off_time, orig_idx, new_msg))
                    else:
                        adjusted_events.append((abs_time, orig_idx, msg))
                else:
                    # No matching note_on found, keep original
                    adjusted_events.append((abs_time, orig_idx, msg))
            else:
                adjusted_events.append((abs_time, orig_idx, msg))
        
        # Sort by absolute time, then by original index for stability
        adjusted_events.sort(key=lambda x: (x[0], x[1]))
        
        # Convert back to delta time
        new_track = mido.MidiTrack()
        prev_time = 0
        
        for abs_time, orig_idx, msg in adjusted_events:
            delta = abs_time - prev_time
            new_msg = msg.copy(time=delta)
            new_track.append(new_msg)
            prev_time = abs_time
        
        new_tracks.append(new_track)
    
    new_midi = mido.MidiFile(ticks_per_beat=midi.ticks_per_beat)
    new_midi.tracks = new_tracks
    return new_midi


def force_channel_zero(midi: mido.MidiFile) -> mido.MidiFile:
    """Set all note events to channel 0 (MIDI channel 1)."""
    new_tracks = []
    
    for track in midi.tracks:
        new_track = mido.MidiTrack()
        for msg in track:
            if msg.type in ('note_on', 'note_off'):
                new_msg = mido.Message(
                    msg.type,
                    channel=0,
                    note=msg.note,
                    velocity=msg.velocity,
                    time=msg.time
                )
                new_track.append(new_msg)
            else:
                new_track.append(msg)
        new_tracks.append(new_track)
    
    new_midi = mido.MidiFile(ticks_per_beat=midi.ticks_per_beat)
    new_midi.tracks = new_tracks
    return new_midi


def set_track_names(midi: mido.MidiFile, track_name: str) -> mido.MidiFile:
    """Set track name for all tracks in the MIDI file."""
    new_tracks = []
    
    for track in midi.tracks:
        new_track = mido.MidiTrack()
        track_name_set = False
        
        for msg in track:
            # Replace existing track_name meta messages
            if msg.type == 'track_name':
                # Replace with new track name, preserve the time
                new_track.append(mido.MetaMessage('track_name', name=track_name, time=msg.time))
                track_name_set = True
            else:
                new_track.append(msg)
        
        # If no track_name was found, add one at the beginning
        if not track_name_set:
            if len(new_track) == 0:
                # Empty track, just add track_name
                new_track.append(mido.MetaMessage('track_name', name=track_name, time=0))
            else:
                # Insert track_name at the beginning
                first_msg = new_track[0]
                if first_msg.time == 0:
                    # First message is at time 0, prepend track_name at time 0
                    new_track.insert(0, mido.MetaMessage('track_name', name=track_name, time=0))
                else:
                    # First message has delay, add track_name with that delay and set first message time to 0
                    track_name_msg = mido.MetaMessage('track_name', name=track_name, time=first_msg.time)
                    new_track.insert(0, track_name_msg)
                    first_msg.time = 0
        
        new_tracks.append(new_track)
    
    new_midi = mido.MidiFile(ticks_per_beat=midi.ticks_per_beat)
    new_midi.tracks = new_tracks
    return new_midi
