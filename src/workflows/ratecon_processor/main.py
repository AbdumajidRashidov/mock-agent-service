#!/usr/bin/env python3
"""
Rate confirmation processor module for extracting data from rate confirmation documents.
"""
# This file is now a thin wrapper around the modular structure
# Import and expose the main entry point
from .processor import process_ratecon

# Keep this export for backward compatibility
__all__ = ['process_ratecon']
