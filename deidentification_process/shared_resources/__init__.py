"""
Shared resources for the deidentification process.

Contains schemas, constants, and utilities used by both the detection
and replacement modules.
"""

from .schemas import (
    PiiType,
    ALL_PII_TYPES,
    PiiOccurrence,
    DistinctPii,
    AnnotatedTranscript,
    Utterance,
    Transcript,
)
from .constants import (
    PII_PRIORITY,
    REDACTION_LABELS,
    GLOBAL_REPLACE_CATEGORIES,
    POSITION_ONLY_CATEGORIES,
)

__all__ = [
    # Types
    "PiiType",
    "ALL_PII_TYPES",
    # Schemas
    "PiiOccurrence",
    "DistinctPii",
    "AnnotatedTranscript",
    "Utterance",
    "Transcript",
    # Constants
    "PII_PRIORITY",
    "REDACTION_LABELS",
    "GLOBAL_REPLACE_CATEGORIES",
    "POSITION_ONLY_CATEGORIES",
]
