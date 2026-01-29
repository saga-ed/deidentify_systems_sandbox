"""
Transcript De-identification Pipeline.

A modular pipeline for detecting and replacing Personally Identifiable
Information (PII) in educational transcript data.

Modules:
    - detection: PII detection using spaCy NER and custom patterns
    - replacement: PII replacement with realistic fake data
    - shared_resources: Common schemas and constants

Quick Start:
    >>> from detection import PiiDetector
    >>> from replacement import TranscriptDeidentifier, create_actions_config
    >>>
    >>> # Detect PII
    >>> detector = PiiDetector()
    >>> ner_result = detector.detect("Hi Maria, I go to Lincoln High School.")
    >>>
    >>> # De-identify
    >>> actions = create_actions_config(default_action="replace")
    >>> deidentifier = TranscriptDeidentifier(seed=42)
    >>> deid_transcript, reid_dict = deidentifier.deidentify(
    ...     ner_result, transcript, actions
    ... )
"""

__version__ = "1.0.0"
