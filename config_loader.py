"""Configuration loader with YAML support."""
import os
import sys
from dataclasses import dataclass
from typing import List, Optional
import yaml


@dataclass
class GlobalConfig:
    """Global transformation settings."""
    strip_to_notes: bool
    force_channel_zero: bool
    ignore_filename_contains: List[str]
    ignore_folders: List[str]
    strip_keep_meta: List[str]


@dataclass
class BassRule:
    """Bass transposition rule."""
    filename_contains: List[str]
    transpose_semitones: int
    track_name: Optional[str] = None


@dataclass
class DrumsRule:
    """Drums note length capping rule."""
    filename_contains: List[str]
    max_note_length: str
    track_name: Optional[str] = None


@dataclass
class WildcardRule:
    """Wildcard rule that applies to files not matching other rules."""
    transpose_semitones: Optional[int] = None
    track_name: Optional[str] = None
    max_note_length: Optional[str] = None


@dataclass
class RulesConfig:
    """Filename-based rules."""
    bass: BassRule
    drums: DrumsRule
    wildcard: Optional[WildcardRule] = None


@dataclass
class Config:
    """Complete application configuration."""
    global_: GlobalConfig
    rules: RulesConfig

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create Config from dictionary."""
        global_data = data.get("global", {})
        rules_data = data.get("rules", {})

        global_config = GlobalConfig(
            strip_to_notes=global_data.get("strip_to_notes", True),
            force_channel_zero=global_data.get("force_channel_zero", True),
            ignore_filename_contains=global_data.get("ignore_filename_contains", []),
            ignore_folders=global_data.get("ignore_folders", []),
            strip_keep_meta=global_data.get("strip_keep_meta", []),
        )

        bass_data = rules_data.get("bass", {})
        bass_rule = BassRule(
            filename_contains=bass_data["filename_contains"],
            transpose_semitones=bass_data["transpose_semitones"],
            track_name=bass_data.get("track_name"),
        )

        drums_data = rules_data.get("drums", {})
        drums_rule = DrumsRule(
            filename_contains=drums_data["filename_contains"],
            max_note_length=drums_data["max_note_length"],
            track_name=drums_data.get("track_name"),
        )

        wildcard_data = rules_data.get("wildcard", {})
        wildcard_rule = None
        if wildcard_data:
            wildcard_rule = WildcardRule(
                transpose_semitones=wildcard_data.get("transpose_semitones"),
                track_name=wildcard_data.get("track_name"),
                max_note_length=wildcard_data.get("max_note_length"),
            )

        rules_config = RulesConfig(bass=bass_rule, drums=drums_rule, wildcard=wildcard_rule)

        return cls(global_=global_config, rules=rules_config)


def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from YAML file.
    
    When running as a packaged executable, looks for config.yaml next to the executable.
    When running as a script, looks for config.yaml in the current directory.
    """
    # Determine base path: next to executable if packaged, otherwise current directory
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = os.path.dirname(sys.executable)
    else:
        # Running as script
        base_path = os.getcwd()
    
    # Build full path to config file
    full_config_path = os.path.join(base_path, config_path)
    
    if not os.path.exists(full_config_path):
        raise FileNotFoundError(
            f"Config file {full_config_path} not found. Please create it next to the executable."
        )
    
    try:
        with open(full_config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return Config.from_dict(data)
    except KeyError as e:
        raise ValueError(f"Missing required config key: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to load config from {full_config_path}: {e}") from e
