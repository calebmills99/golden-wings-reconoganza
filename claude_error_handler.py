"""
Claude AI Chat Data Error Handler Module

Manages errors, provides recovery mechanisms, and logs issues during extraction.
Ensures robust operation with graceful degradation.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    FILE_IO = "file_io"
    JSON_PARSING = "json_parsing"
    DATA_VALIDATION = "data_validation"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


@dataclass
class ErrorRecord:
    """Record of an error occurrence."""
    timestamp: datetime
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    recoverable: bool = True
    retry_count: int = 0


@dataclass
class ErrorSummary:
    """Summary of errors by category and severity."""
    total_errors: int
    errors_by_category: Dict[str, int]
    errors_by_severity: Dict[str, int]
    recoverable_errors: int
    unrecoverable_errors: int


class ErrorHandler:
    """Handles errors and recovery for the extraction pipeline."""

    def __init__(self, max_errors: int = 1000, log_file: Optional[str] = None):
        """
        Initialize error handler.

        Args:
            max_errors: Maximum number of errors to store
            log_file: Optional file to log errors to
        """
        self.errors: List[ErrorRecord] = []
        self.max_errors = max_errors
        self.log_file = log_file
        self.recovery_actions = {
            ErrorCategory.FILE_IO: self._recover_file_io,
            ErrorCategory.JSON_PARSING: self._recover_json_parsing,
            ErrorCategory.DATA_VALIDATION: self._recover_data_validation,
            ErrorCategory.NETWORK: self._recover_network,
        }

    def log_error(self, category: str, message: str, details: Optional[str] = None,
                  severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                  context: Optional[Dict[str, Any]] = None,
                  recoverable: bool = True) -> ErrorRecord:
        """
        Log an error.

        Args:
            category: Error category
            message: Error message
            details: Additional error details
            severity: Error severity level
            context: Additional context information
            recoverable: Whether the error is recoverable

        Returns:
            ErrorRecord for the logged error
        """
        try:
            error_category = ErrorCategory(category.lower())
        except ValueError:
            error_category = ErrorCategory.UNKNOWN

        error_record = ErrorRecord(
            timestamp=datetime.now(),
            category=error_category,
            severity=severity,
            message=message,
            details=details,
            context=context or {},
            recoverable=recoverable
        )

        self.errors.append(error_record)

        # Trim errors if we exceed max
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]

        # Log to file if configured
        if self.log_file:
            self._write_to_log_file(error_record)

        # Print error based on severity
        self._print_error(error_record)

        return error_record

    def attempt_recovery(self, error_record: ErrorRecord) -> bool:
        """
        Attempt to recover from an error.

        Args:
            error_record: The error to recover from

        Returns:
            True if recovery was successful
        """
        if not error_record.recoverable:
            return False

        recovery_func = self.recovery_actions.get(error_record.category)
        if recovery_func:
            try:
                success = recovery_func(error_record)
                if success:
                    error_record.retry_count += 1
                    print(f"🔄 Recovery successful for {error_record.category.value} error")
                    return True
                else:
                    print(f"❌ Recovery failed for {error_record.category.value} error")
            except Exception as e:
                print(f"❌ Recovery exception: {e}")

        return False

    def get_error_summary(self) -> ErrorSummary:
        """Get a summary of all errors."""
        errors_by_category = {}
        errors_by_severity = {}
        recoverable = 0
        unrecoverable = 0

        for error in self.errors:
            # Count by category
            cat_key = error.category.value
            errors_by_category[cat_key] = errors_by_category.get(cat_key, 0) + 1

            # Count by severity
            sev_key = error.severity.value
            errors_by_severity[sev_key] = errors_by_severity.get(sev_key, 0) + 1

            # Count recoverable vs unrecoverable
            if error.recoverable:
                recoverable += 1
            else:
                unrecoverable += 1

        return ErrorSummary(
            total_errors=len(self.errors),
            errors_by_category=errors_by_category,
            errors_by_severity=errors_by_severity,
            recoverable_errors=recoverable,
            unrecoverable_errors=unrecoverable
        )

    def should_abort_pipeline(self, error_record: ErrorRecord) -> bool:
        """
        Determine if the pipeline should abort based on error severity.

        Args:
            error_record: The error to evaluate

        Returns:
            True if pipeline should abort
        """
        return error_record.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]

    def clear_errors(self):
        """Clear all logged errors."""
        self.errors.clear()
        print("🧹 Error log cleared")

    def _print_error(self, error: ErrorRecord):
        """Print error to console based on severity."""
        severity_emoji = {
            ErrorSeverity.LOW: "ℹ️",
            ErrorSeverity.MEDIUM: "⚠️",
            ErrorSeverity.HIGH: "🚨",
            ErrorSeverity.CRITICAL: "💥"
        }.get(error.severity, "❗️")

        category_display = error.category.value.replace('_', ' ').title()

        print(f"{severity_emoji} {category_display} Error: {error.message}")

        if error.details:
            print(f"   📝 Details: {error.details}")

    def _write_to_log_file(self, error: ErrorRecord):
        """Write error to log file."""
        try:
            log_entry = {
                "timestamp": error.timestamp.isoformat(),
                "category": error.category.value,
                "severity": error.severity.value,
                "message": error.message,
                "details": error.details,
                "context": error.context,
                "recoverable": error.recoverable,
                "retry_count": error.retry_count
            }

            with open(self.log_file, 'a', encoding='utf-8') as f:
                json.dump(log_entry, f, default=str)
                f.write('\n')

        except Exception as e:
            print(f"⚠️  Failed to write to error log: {e}")

    def _recover_file_io(self, error: ErrorRecord) -> bool:
        """Attempt recovery from file I/O errors."""
        # For file I/O errors, we might try alternative paths or wait and retry
        if "file not found" in error.message.lower():
            # Could try alternative file extensions or paths
            return False  # Not implemented in basic version

        return False

    def _recover_json_parsing(self, error: ErrorRecord) -> bool:
        """Attempt recovery from JSON parsing errors."""
        # For JSON parsing errors, we might try alternative parsing approaches
        # or skip the problematic file
        return False  # Skip file for now

    def _recover_data_validation(self, error: ErrorRecord) -> bool:
        """Attempt recovery from data validation errors."""
        # For validation errors, we might try to fix common issues
        # or use default values
        return False  # Skip invalid data

    def _recover_network(self, error: ErrorRecord) -> bool:
        """Attempt recovery from network errors."""
        # For network errors, we might retry with backoff
        if error.retry_count < 3:
            import time
            time.sleep(1 * (2 ** error.retry_count))  # Exponential backoff
            return True

        return False

    def print_error_summary(self):
        """Print a summary of errors."""
        summary = self.get_error_summary()

        if summary.total_errors == 0:
            print("✅ No errors recorded")
            return

        print(f"\n📊 Error Summary ({summary.total_errors} total)")
        print("=" * 50)

        print(f"🔄 Recoverable: {summary.recoverable_errors}")
        print(f"❌ Unrecoverable: {summary.unrecoverable_errors}")

        if summary.errors_by_severity:
            print("\n🚨 By Severity:")
            for severity, count in summary.errors_by_severity.items():
                print(f"   {severity.title()}: {count}")

        if summary.errors_by_category:
            print("\n📂 By Category:")
            for category, count in summary.errors_by_category.items():
                print(f"   {category.title()}: {count}")

        print("=" * 50)