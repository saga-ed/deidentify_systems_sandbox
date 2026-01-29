#!/usr/bin/env python3
"""
PII Detection CLI Application.

Provides a command-line interface for detecting PII in transcript files.

Usage:
    python -m detection.app detect input.txt
    python -m detection.app detect input.txt -o output.json
    python -m detection.app detect input.txt --model en_core_web_sm

Examples:
    # Detect PII and print to stdout
    python -m detection.app detect transcript.txt

    # Detect PII and save to JSON file
    python -m detection.app detect transcript.txt -o results.json

    # Use a smaller/faster model
    python -m detection.app detect transcript.txt --model en_core_web_sm
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from detection.detector import PiiDetector
from detection.settings import DetectorSettings


def detect_pii(
    input_path: str,
    output_path: str | None = None,
    model_name: str = "en_core_web_lg",
    pretty: bool = True,
) -> dict:
    """Detect PII in a transcript file.

    Args:
        input_path: Path to input transcript file
        output_path: Optional path for output JSON file
        model_name: spaCy model to use
        pretty: Whether to pretty-print JSON output

    Returns:
        Dictionary with detection results
    """
    # Initialize detector
    settings = DetectorSettings(model_name=model_name)
    detector = PiiDetector(settings=settings)

    # Read input file
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    text = input_file.read_text(encoding="utf-8")

    # Detect PII
    result = detector.detect(text)

    # Convert to dictionary
    result_dict = {
        "distinct_pii": result.distinct_pii.to_dict(),
        "pii_occurrences": [
            {
                "start": occ.start,
                "end": occ.end,
                "text": occ.text,
                "pii_type": occ.pii_type,
            }
            for occ in result.pii_occurrences
        ],
        "transcript": text,  # Required for position-based replacements
        "statistics": {
            "total_distinct": result.distinct_pii.count(),
            "total_occurrences": len(result.pii_occurrences),
            "by_type": {
                pii_type: len(result.distinct_pii.get(pii_type))
                for pii_type in ["NAME", "LOCATION", "SCHOOL", "DATE", "AGE",
                                "PHONE", "EMAIL", "URL", "MISC_ID"]
            }
        }
    }

    # Output results
    indent = 2 if pretty else None

    if output_path:
        output_file = Path(output_path)
        output_file.write_text(
            json.dumps(result_dict, indent=indent, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"Results saved to: {output_path}")
    else:
        print(json.dumps(result_dict, indent=indent, ensure_ascii=False))

    return result_dict


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PII Detection CLI for transcript de-identification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s detect transcript.txt
    %(prog)s detect transcript.txt -o results.json
    %(prog)s detect transcript.txt --model en_core_web_sm
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Detect command
    detect_parser = subparsers.add_parser(
        "detect",
        help="Detect PII in a transcript file"
    )
    detect_parser.add_argument(
        "input",
        help="Path to input transcript file"
    )
    detect_parser.add_argument(
        "-o", "--output",
        help="Path to output JSON file (prints to stdout if not specified)"
    )
    detect_parser.add_argument(
        "--model",
        default="en_core_web_lg",
        help="spaCy model to use (default: en_core_web_lg)"
    )
    detect_parser.add_argument(
        "--compact",
        action="store_true",
        help="Output compact JSON (no indentation)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "detect":
        try:
            detect_pii(
                input_path=args.input,
                output_path=args.output,
                model_name=args.model,
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
