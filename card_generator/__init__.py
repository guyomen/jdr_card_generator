"""
JDR Card Generator - Générateur de cartes JDR avec support IA
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__license__ = "MIT"

from .generator import CardGenerator
from .exceptions import CardGeneratorError

__all__ = ["CardGenerator", "CardGeneratorError"]
