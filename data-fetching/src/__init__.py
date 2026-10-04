"""
Wikipedia Senate Election & Polling Scraper Package.
URV - Visualització d'Informació (MiV) - Pràctica 1.
"""

try:
    from .main import main
except ImportError:
    from main import main

__all__ = ["main"]
