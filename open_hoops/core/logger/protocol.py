from typing import Protocol


class LoggerProtocol(Protocol):
    """Logger class that has a simple write method."""

    def info(self, message: str, *args, **kwargs) -> None:
        """Log info message."""

    def warning(self, message: str, *args, **kwargs) -> None:
        """Log warning message."""

    def error(self, message: str, *args, **kwargs) -> None:
        """Log error message."""
