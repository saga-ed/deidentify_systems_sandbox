"""
PII Replacement Module.

Provides de-identification functionality for transcripts by replacing
detected PII with realistic fake data or redaction labels.

Usage:
    from replacement import TranscriptDeidentifier, ReplacementGenerator

    # Create generator and deidentifier
    generator = ReplacementGenerator(seed=42)
    deidentifier = TranscriptDeidentifier(generator=generator)

    # De-identify transcript using NER results
    deid_transcript, reid_dict = deidentifier.deidentify(
        ner_result, transcript, actions
    )

CLI:
    python -m replacement.app deidentify input.json --ner ner_result.json -o output.json
"""

from .replacement_generator import (
    ReplacementGenerator,
    create_replacement_generator,
    create_actions_config,
)
from .deidentifier import (
    TranscriptDeidentifier,
    deidentify_transcript,
)
from .name_replacer import (
    NameReplacer,
    detect_name_type,
    detect_gender,
    detect_country,
)

__all__ = [
    # Main classes
    "TranscriptDeidentifier",
    "ReplacementGenerator",
    "NameReplacer",
    # Factory functions
    "create_replacement_generator",
    "create_actions_config",
    "deidentify_transcript",
    # Utility functions
    "detect_name_type",
    "detect_gender",
    "detect_country",
]
