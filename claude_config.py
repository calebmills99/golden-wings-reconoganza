"""
Claude AI Chat Data Extraction Configuration Module

Manages configuration settings for the Claude AI conversation extraction pipeline.
Provides default settings and validation for processing parameters.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ProcessingConfig:
    """Configuration for data processing pipeline."""
    batch_size: int = 100
    max_workers: int = 4
    memory_limit_mb: int = 2048
    timeout_seconds: int = 300
    enable_progress_tracking: bool = True
    enable_error_recovery: bool = True


@dataclass
class ExtractionConfig:
    """Configuration for data extraction features."""
    enable_summaries: bool = True
    enable_categorization: bool = True
    enable_entity_extraction: bool = True
    max_content_length: int = 50000
    min_message_length: int = 10
    extract_attachments: bool = True


@dataclass
class OutputConfig:
    """Configuration for output formats and destinations."""
    formats: list = None
    output_directory: str = "./claude_extraction_output"
    compression: bool = True
    include_raw_data: bool = False
    timestamp_format: str = "%Y%m%d_%H%M%S"

    def __post_init__(self):
        if self.formats is None:
            self.formats = ["json", "csv", "markdown"]


@dataclass
class NotionConfig:
    """Configuration for Notion integration."""
    enabled: bool = False
    database_name: str = "Claude Conversations"
    batch_size: int = 50
    rate_limit_delay: float = 0.1
    max_retries: int = 3


@dataclass
class ClaudeExtractorConfig:
    """Main configuration class for Claude AI extractor."""
    source_directory: str = r"F:\dev\quivr"
    processing: ProcessingConfig = None
    extraction: ExtractionConfig = None
    output: OutputConfig = None
    notion: NotionConfig = None

    def __post_init__(self):
        if self.processing is None:
            self.processing = ProcessingConfig()
        if self.extraction is None:
            self.extraction = ExtractionConfig()
        if self.output is None:
            self.output = OutputConfig()
        if self.notion is None:
            self.notion = NotionConfig()


class ConfigManager:
    """Manages configuration loading, validation, and access."""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_file: Path to JSON configuration file (optional)
        """
        self.config = ClaudeExtractorConfig()

        if config_file and Path(config_file).exists():
            self.load_from_file(config_file)

        self._validate_config()

    def load_from_file(self, config_file: str) -> None:
        """
        Load configuration from JSON file.

        Args:
            config_file: Path to configuration file
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Update main config
            for key, value in data.items():
                if hasattr(self.config, key):
                    if isinstance(value, dict):
                        # Handle nested dataclasses
                        current_value = getattr(self.config, key)
                        if hasattr(current_value, '__dict__'):
                            for sub_key, sub_value in value.items():
                                if hasattr(current_value, sub_key):
                                    setattr(current_value, sub_key, sub_value)
                    else:
                        setattr(self.config, key, value)

            print("✅ Configuration loaded from file")
            print(f"   📁 Source: {config_file}")

        except Exception as e:
            print(f"⚠️  Failed to load config from {config_file}: {e}")
            print("   📋 Using default configuration")

    def save_to_file(self, config_file: str) -> None:
        """
        Save current configuration to JSON file.

        Args:
            config_file: Path to save configuration file
        """
        try:
            Path(config_file).parent.mkdir(parents=True, exist_ok=True)

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.config), f, indent=2, default=str)

            print("💾 Configuration saved to file")
            print(f"   📁 Destination: {config_file}")

        except Exception as e:
            print(f"❌ Failed to save config to {config_file}: {e}")

    def _validate_config(self) -> None:
        """Validate configuration settings."""
        errors = []

        # Validate source directory
        if not Path(self.config.source_directory).exists():
            errors.append(f"Source directory does not exist: {self.config.source_directory}")

        # Validate batch size
        if self.config.processing.batch_size < 1:
            errors.append("Batch size must be positive")

        # Validate output directory
        if not self.config.output.output_directory:
            errors.append("Output directory cannot be empty")

        # Validate formats
        valid_formats = ["json", "csv", "markdown", "sqlite"]
        for fmt in self.config.output.formats:
            if fmt not in valid_formats:
                errors.append(f"Invalid output format: {fmt}")

        if errors:
            print("⚠️  Configuration validation errors:")
            for error in errors:
                print(f"   ❌ {error}")
        else:
            print("✅ Configuration validation passed")

    def get_config(self) -> ClaudeExtractorConfig:
        """Get the current configuration."""
        return self.config

    def update_config(self, updates: Dict[str, Any]) -> None:
        """
        Update configuration with new values.

        Args:
            updates: Dictionary of configuration updates
        """
        for key, value in updates.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        self._validate_config()

    def print_config_summary(self) -> None:
        """Print a summary of current configuration."""
        print("\n🔧 Claude AI Extractor Configuration Summary")
        print("=" * 50)
        print(f"📂 Source Directory: {self.config.source_directory}")
        print(f"📦 Batch Size: {self.config.processing.batch_size}")
        print(f"⚡ Max Workers: {self.config.processing.max_workers}")
        print(f"💾 Output Directory: {self.config.output.output_directory}")
        print(f"📋 Output Formats: {', '.join(self.config.output.formats)}")
        print(f"🗃️  Notion Integration: {'Enabled' if self.config.notion.enabled else 'Disabled'}")
        print(f"📊 Progress Tracking: {'Enabled' if self.config.processing.enable_progress_tracking else 'Disabled'}")
        print(f"🛡️  Error Recovery: {'Enabled' if self.config.processing.enable_error_recovery else 'Disabled'}")
        print("=" * 50)


# Global configuration instance
_config_manager = None


def get_config_manager(config_file: Optional[str] = None) -> ConfigManager:
    """
    Get the global configuration manager instance.

    Args:
        config_file: Path to configuration file (optional)

    Returns:
        ConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_file)
    return _config_manager


def get_config() -> ClaudeExtractorConfig:
    """
    Get the current configuration.

    Returns:
        ClaudeExtractorConfig instance
    """
    return get_config_manager().get_config()


if __name__ == "__main__":
    # Test configuration
    config_manager = get_config_manager()
    config_manager.print_config_summary()