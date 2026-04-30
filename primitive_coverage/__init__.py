"""Generic primitive coverage scanner for Cognitive OS and arbitrary repositories."""

from .model import CoverageReport, PrimitiveRow
from .scanner import scan_repository

__all__ = ["CoverageReport", "PrimitiveRow", "scan_repository"]
