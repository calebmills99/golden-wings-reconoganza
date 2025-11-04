"""
Claude AI Chat Data Progress Tracker Module

Tracks progress, timing, and performance metrics for the extraction pipeline.
Provides real-time feedback and completion estimates.
"""

from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class PhaseMetrics:
    """Metrics for a processing phase."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    items_processed: int = 0
    items_total: int = 0
    status: str = "pending"  # pending, running, completed, failed


@dataclass
class ProgressMetrics:
    """Overall progress metrics."""
    phases: Dict[str, PhaseMetrics] = field(default_factory=dict)
    total_start_time: Optional[datetime] = None
    total_end_time: Optional[datetime] = None
    current_phase: Optional[str] = None


class ProgressTracker:
    """Tracks progress and timing for extraction operations."""

    def __init__(self):
        """Initialize progress tracker."""
        self.metrics = ProgressMetrics()
        self.overall_start_time = None

    def start_overall(self):
        """Start overall tracking."""
        self.overall_start_time = datetime.now()
        self.metrics.total_start_time = self.overall_start_time
        print(f"🚀 Started extraction pipeline at {self.overall_start_time.strftime('%H:%M:%S')}")

    def end_overall(self):
        """End overall tracking."""
        if self.overall_start_time:
            self.metrics.total_end_time = datetime.now()
            total_duration = (self.metrics.total_end_time - self.overall_start_time).total_seconds()
            print(f"🏁 Completed extraction pipeline in {total_duration:.2f}s")

    def start_phase(self, phase_name: str, total_items: Optional[int] = None):
        """
        Start tracking a processing phase.

        Args:
            phase_name: Name of the phase
            total_items: Total items to process (optional)
        """
        if phase_name not in self.metrics.phases:
            self.metrics.phases[phase_name] = PhaseMetrics()

        phase = self.metrics.phases[phase_name]
        phase.start_time = datetime.now()
        phase.status = "running"
        phase.items_total = total_items or 0
        self.metrics.current_phase = phase_name

        phase_name_display = phase_name.replace('_', ' ').title()
        print(f"▶️  Starting {phase_name_display}...")

    def update_phase_progress(self, phase_name: str, items_processed: int):
        """
        Update progress for a phase.

        Args:
            phase_name: Name of the phase
            items_processed: Number of items processed so far
        """
        if phase_name in self.metrics.phases:
            phase = self.metrics.phases[phase_name]
            phase.items_processed = items_processed

            if phase.items_total > 0:
                progress_pct = (items_processed / phase.items_total) * 100
                print(f"   📊 {phase_name}: {items_processed}/{phase.items_total} ({progress_pct:.1f}%)")

    def end_phase(self, phase_name: str, duration_override: Optional[float] = None) -> float:
        """
        End tracking for a phase.

        Args:
            phase_name: Name of the phase
            duration_override: Override calculated duration

        Returns:
            Duration in seconds
        """
        if phase_name not in self.metrics.phases:
            return 0.0

        phase = self.metrics.phases[phase_name]
        phase.end_time = datetime.now()

        if duration_override is not None:
            phase.duration = duration_override
        elif phase.start_time:
            phase.duration = (phase.end_time - phase.start_time).total_seconds()

        phase.status = "completed"

        phase_name_display = phase_name.replace('_', ' ').title()
        print(f"✅ Completed {phase_name_display} in {phase.duration:.2f}s")

        return phase.duration

    def fail_phase(self, phase_name: str, error_message: str):
        """
        Mark a phase as failed.

        Args:
            phase_name: Name of the phase
            error_message: Error description
        """
        if phase_name in self.metrics.phases:
            phase = self.metrics.phases[phase_name]
            phase.end_time = datetime.now()
            phase.status = "failed"

            if phase.start_time:
                phase.duration = (phase.end_time - phase.start_time).total_seconds()

        phase_name_display = phase_name.replace('_', ' ').title()
        print(f"❌ Failed {phase_name_display}: {error_message}")

    def get_total_time(self) -> float:
        """Get total processing time."""
        if not self.metrics.total_start_time or not self.metrics.total_end_time:
            return 0.0
        return (self.metrics.total_end_time - self.metrics.total_start_time).total_seconds()

    def get_phase_times(self) -> Dict[str, float]:
        """Get timing for all phases."""
        return {name: phase.duration for name, phase in self.metrics.phases.items()}

    def get_current_progress(self) -> Dict[str, any]:
        """Get current progress information."""
        return {
            "current_phase": self.metrics.current_phase,
            "total_time": self.get_total_time(),
            "phase_times": self.get_phase_times(),
            "phases": {
                name: {
                    "status": phase.status,
                    "duration": phase.duration,
                    "progress": f"{phase.items_processed}/{phase.items_total}" if phase.items_total > 0 else "N/A"
                }
                for name, phase in self.metrics.phases.items()
            }
        }

    def print_progress_summary(self):
        """Print a summary of progress."""
        print("\n📊 Progress Summary")
        print("=" * 40)

        total_time = self.get_total_time()
        if total_time > 0:
            print(f"⏱️  Total Time: {total_time:.2f}s")

        for phase_name, phase in self.metrics.phases.items():
            phase_display = phase_name.replace('_', ' ').title()
            status_emoji = {
                "pending": "⏳",
                "running": "▶️",
                "completed": "✅",
                "failed": "❌"
            }.get(phase.status, "❓")

            print(f"{status_emoji} {phase_display}: {phase.duration:.2f}s")

        print("=" * 40)