#!/usr/bin/env python3
"""
PII Replacement CLI Application.

Provides a command-line interface for de-identifying transcripts.

Usage:
    python -m replacement.app deidentify transcript.json --ner ner_result.json -o output.json
    python -m replacement.app deidentify transcript.json --ner ner_result.json --seed 42

Examples:
    # De-identify with default settings
    python -m replacement.app deidentify transcript.json --ner detected_pii.json

    # De-identify with seed for reproducibility
    python -m replacement.app deidentify transcript.json --ner detected_pii.json --seed 42 -o deid.json

    # De-identify with redaction for some types
    python -m replacement.app deidentify transcript.json --ner detected_pii.json --redact EMAIL PHONE
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared_resources import AnnotatedTranscript, DistinctPii, PiiOccurrence, PiiType
from replacement.deidentifier import TranscriptDeidentifier
from replacement.replacement_generator import create_actions_config


def load_ner_result(ner_path: str) -> AnnotatedTranscript:
    """Load NER result from JSON file.

    Args:
        ner_path: Path to NER result JSON file

    Returns:
        AnnotatedTranscript instance
    """
    with open(ner_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Build DistinctPii
    distinct_pii = DistinctPii()
    for pii_type, items in data.get("distinct_pii", {}).items():
        for item in items:
            distinct_pii.add(pii_type, item)

    # Build occurrences
    occurrences = [
        PiiOccurrence(
            start=occ["start"],
            end=occ["end"],
            text=occ["text"],
            pii_type=occ["pii_type"],
        )
        for occ in data.get("pii_occurrences", [])
    ]

    # Get transcript text
    transcript = data.get("transcript", "")

    return AnnotatedTranscript(
        distinct_pii=distinct_pii,
        pii_occurrences=occurrences,
        transcript=transcript,
    )


def deidentify_file(
    transcript_path: str,
    ner_path: str,
    output_path: Optional[str] = None,
    reid_path: Optional[str] = None,
    seed: Optional[int] = None,
    redact_types: Optional[list[PiiType]] = None,
    pretty: bool = True,
) -> tuple[dict, dict]:
    """De-identify a transcript file.

    Args:
        transcript_path: Path to transcript JSON file
        ner_path: Path to NER result JSON file
        output_path: Optional path for de-identified output
        reid_path: Optional path for re-identification dict
        seed: Random seed for reproducibility
        redact_types: PII types to redact instead of replace
        pretty: Whether to pretty-print JSON output

    Returns:
        Tuple of (de-identified transcript, re-identification dict)
    """
    # Load transcript
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    # Load NER result
    ner_result = load_ner_result(ner_path)

    # Configure actions
    actions = create_actions_config(
        default_action="replace",
        redact=redact_types,
    )

    # Create deidentifier
    deidentifier = TranscriptDeidentifier(seed=seed)

    # De-identify
    deid_transcript, reid_dict = deidentifier.deidentify(ner_result, transcript, actions)

    # Output results
    indent = 2 if pretty else None

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(deid_transcript, f, indent=indent, ensure_ascii=False)
        print(f"De-identified transcript saved to: {output_path}")

    if reid_path:
        with open(reid_path, "w", encoding="utf-8") as f:
            json.dump(reid_dict, f, indent=indent, ensure_ascii=False)
        print(f"Re-identification dict saved to: {reid_path}")

    if not output_path:
        print(json.dumps(deid_transcript, indent=indent, ensure_ascii=False))

    return deid_transcript, reid_dict


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PII Replacement CLI for transcript de-identification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s deidentify transcript.json --ner detected_pii.json
    %(prog)s deidentify transcript.json --ner detected_pii.json -o deid.json --reid reid.json
    %(prog)s deidentify transcript.json --ner detected_pii.json --seed 42
    %(prog)s deidentify transcript.json --ner detected_pii.json --redact EMAIL PHONE
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Deidentify command
    deid_parser = subparsers.add_parser(
        "deidentify",
        help="De-identify a transcript file"
    )
    deid_parser.add_argument(
        "transcript",
        help="Path to transcript JSON file"
    )
    deid_parser.add_argument(
        "--ner",
        required=True,
        help="Path to NER result JSON file"
    )
    deid_parser.add_argument(
        "-o", "--output",
        help="Path to output de-identified transcript (prints to stdout if not specified)"
    )
    deid_parser.add_argument(
        "--reid",
        help="Path to output re-identification dict"
    )
    deid_parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducible replacements"
    )
    deid_parser.add_argument(
        "--redact",
        nargs="+",
        choices=["NAME", "LOCATION", "SCHOOL", "DATE", "AGE", "PHONE", "EMAIL", "URL", "MISC_ID"],
        help="PII types to redact instead of replace"
    )
    deid_parser.add_argument(
        "--compact",
        action="store_true",
        help="Output compact JSON (no indentation)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "deidentify":
        try:
            deidentify_file(
                transcript_path=args.transcript,
                ner_path=args.ner,
                output_path=args.output,
                reid_path=args.reid,
                seed=args.seed,
                redact_types=args.redact,
                pretty=not args.compact,
            )
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
