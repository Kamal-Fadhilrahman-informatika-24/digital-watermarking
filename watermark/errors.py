"""Custom exceptions. Messages are written for end users (Bahasa Indonesia)."""

from __future__ import annotations


class WatermarkError(Exception):
    """Base class for all expected, user-facing watermarking errors."""


class ImageValidationError(WatermarkError):
    """Uploaded file is not a usable image."""


class CapacityError(WatermarkError):
    """Watermark does not fit inside the image."""


class PayloadError(WatermarkError):
    """Payload header/CRC is missing or invalid."""
