"""Pydantic AI Load Reply Processor

A modern AI-powered freight negotiation system built with Pydantic AI.
Compatible with existing gRPC interface for drop-in replacement.
"""

from .main import process_reply

__version__ = "1.0.0"
__all__ = ["process_reply"]
