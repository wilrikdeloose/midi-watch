# MIDI Watcher/Transformer

A Python application that watches for MIDI files and transforms them according to configuration rules.

## Building the Executable

To build a standalone executable from the source code:

### Prerequisites

1. Install Python 3.8 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

### Build Steps

1. Run PyInstaller using the provided spec file:
   ```bash
   pyinstaller midi-watch.spec
   ```

2. The executable will be created in the `dist/` folder as `midi-watch.exe` (Windows) or `midi-watch` (Linux/Mac).

3. Copy `config.yaml` to the same directory as the executable.

### Rebuilding

After making code changes, rebuild the executable by running the same command:
```bash
pyinstaller midi-watch.spec
```

**Note**: The executable looks for `config.yaml` in the same directory as the executable file. Make sure to place both files together when distributing or using the app.

## Configuration

The application is configured via `config.yaml`, which must be placed next to the executable (or in the current directory when running as a script).

### Configuration Structure

```yaml
global:
  strip_to_notes: <boolean>
  force_channel_zero: <boolean>

rules:
  bass:
    filename_contains: <list of strings>
    transpose_semitones: <integer>
    track_name: <string (optional)>
  drums:
    filename_contains: <list of strings>
    max_note_length: <string>
  wildcard:
    transpose_semitones: <integer (optional)>
    track_name: <string (optional)>
    max_note_length: <string (optional)>
```

### Global Settings

#### `global.strip_to_notes`
- **Type**: `boolean`
- **Description**: If `true`, strips all MIDI events except note events (note_on, note_off) and end_of_track meta messages. Preserves correct timing by carrying delta ticks from removed events into the next kept event.
- **Example**: `strip_to_notes: true`

#### `global.force_channel_zero`
- **Type**: `boolean`
- **Description**: If `true`, sets all note events to MIDI channel 0 (channel 1 in MIDI terminology).
- **Example**: `force_channel_zero: true`

### Rules

#### Bass Rule (`rules.bass`)

Applies transposition to files whose names contain specified keywords.

##### `rules.bass.filename_contains`
- **Type**: `list of strings`
- **Description**: List of case-insensitive keywords to match in filenames. If any keyword is found, the rule applies.
- **Example**: 
  ```yaml
  filename_contains:
    - "bass"
    - "bassline"
  ```

##### `rules.bass.transpose_semitones`
- **Type**: `integer`
- **Description**: Number of semitones to transpose notes up. Values are clamped to the valid MIDI note range (0-127).
- **Example**: `transpose_semitones: 12` (transposes up one octave)

##### `rules.bass.track_name`
- **Type**: `string` (optional)
- **Description**: Track name to set for all tracks in matching MIDI files. If specified, replaces or adds a track_name meta message to each track.
- **Example**: `track_name: "Bass"`

#### Drums Rule (`rules.drums`)

Caps note lengths for files whose names contain specified keywords.

##### `rules.drums.filename_contains`
- **Type**: `list of strings`
- **Description**: List of case-insensitive keywords to match in filenames. If any keyword is found, the rule applies.
- **Example**:
  ```yaml
  filename_contains:
    - "drum"
    - "drums"
    - "percussion"
  ```

##### `rules.drums.max_note_length`
- **Type**: `string`
- **Description**: Maximum note length in musical time notation. Currently only `"1/8"` (eighth note) is supported.
- **Example**: `max_note_length: "1/8"`

##### `rules.drums.track_name`
- **Type**: `string` (optional)
- **Description**: Track name to set for all tracks in matching MIDI files. If specified, replaces or adds a track_name meta message to each track.
- **Example**: `track_name: "Drums"`

#### Wildcard Rule (`rules.wildcard`)

Applies to files that don't match any other filename-based rules (bass or drums). All fields are optional.

##### `rules.wildcard.transpose_semitones`
- **Type**: `integer` (optional)
- **Description**: Number of semitones to transpose notes up. Values are clamped to the valid MIDI note range (0-127). Only applied if specified.
- **Example**: `transpose_semitones: 0`

##### `rules.wildcard.track_name`
- **Type**: `string` (optional)
- **Description**: Track name to set for all tracks in matching MIDI files. Only applied if specified.
- **Example**: `track_name: "Other"`

##### `rules.wildcard.max_note_length`
- **Type**: `string` (optional)
- **Description**: Maximum note length in musical time notation. Currently only `"1/8"` (eighth note) is supported. Only applied if specified.
- **Example**: `max_note_length: "1/8"`

**Note**: The wildcard rule only applies when the filename does NOT match the bass or drums rules. If a file matches bass or drums, the wildcard rule is ignored.

### Example Configuration

```yaml
global:
  strip_to_notes: true
  force_channel_zero: true

rules:
  bass:
    filename_contains:
      - "bass"
      - "bassline"
    transpose_semitones: 12
    track_name: "Bass"
  drums:
    filename_contains:
      - "drum"
      - "drums"
    max_note_length: "1/8"
    track_name: "Drums"
  wildcard:
    track_name: "Other"
```

## Transformation Order

Transformations are applied in the following order:

1. **Global strip to notes** (if enabled): Removes all events except notes and end_of_track, preserving timing
2. **Bass transposition** (if filename matches): Transposes notes up by specified semitones
3. **Bass track name** (if filename matches and track_name is set): Sets track name for all tracks
4. **Drums note length cap** (if filename matches): Caps note lengths to maximum specified
5. **Drums track name** (if filename matches and track_name is set): Sets track name for all tracks
6. **Wildcard rule** (if filename doesn't match bass/drums and wildcard is configured): Applies optional transpose, track name, and/or note length cap
6. **Global force channel zero** (if enabled): Sets all notes to channel 0

## Behavior

- The application scans the current working directory recursively for `.mid` and `.midi` files
- Files are processed and overwritten in place using atomic writes
- After initial scan, the application watches for file changes
- Changes are debounced by 1.0 second per file
- Self-writes are suppressed to avoid infinite loops
- If processed content is identical to original, the file is not rewritten
