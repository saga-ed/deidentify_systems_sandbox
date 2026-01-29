"""
PII Detection Module.

Provides spaCy-based PII detection for transcript de-identification.
Designed for ASR (Automatic Speech Recognition) transcripts from
educational tutoring sessions.

Usage:
    from detection import PiiDetector, detect_pii

    # Simple usage
    result = detect_pii("Hi, my name is John and I'm from Chicago.")

    # Or with detector instance for configuration
    detector = PiiDetector()
    result = detector.detect(text)

CLI:
    python -m detection.app detect input.txt -o output.json
"""

from .detector import PiiDetector
from .settings import DetectorSettings

__all__ = [
    "PiiDetector",
    "DetectorSettings",
]


def detect_pii(text: str) -> "AnnotatedTranscript":
    """Convenience function to detect PII in text.

    Args:
        text: The transcript text to analyze

    Returns:
        AnnotatedTranscript with detected PII
    """
    from shared_resources import AnnotatedTranscript

    detector = PiiDetector()
    return detector.detect(text)
