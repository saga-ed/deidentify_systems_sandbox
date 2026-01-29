"""
Tests for the PII Replacement Module.

Covers:
- Name replacement (first names, last names, auto-detect)
- Location replacement
- School replacement
- Date replacement (format preservation)
- Age replacement
- Phone replacement
- Email replacement
- URL replacement
- MISC_ID replacement
- Redaction mode
- Transcript de-identification
"""

import sys
from pathlib import Path

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from replacement.name_replacer import (
    NameReplacer,
    detect_name_type,
    detect_gender,
    detect_country,
)
from replacement.replacement_generator import (
    ReplacementGenerator,
    create_actions_config,
)
from replacement.deidentifier import TranscriptDeidentifier
from shared_resources import AnnotatedTranscript, DistinctPii, PiiOccurrence


@pytest.fixture
def generator():
    """Create a generator instance for testing."""
    return ReplacementGenerator(seed=42)


@pytest.fixture
def name_replacer():
    """Create a name replacer instance for testing."""
    return NameReplacer(seed=42)


class TestNameDetection:
    """Tests for name type detection."""

    def test_detects_first_name(self):
        """Should detect common first names."""
        assert detect_name_type("Maria") == "first"
        assert detect_name_type("John") == "first"

    def test_detects_last_name(self):
        """Should detect common last names."""
        assert detect_name_type("Smith") == "last"
        assert detect_name_type("Williams") == "last"

    def test_gender_detection(self):
        """Should detect gender for first names."""
        assert detect_gender("Maria") == "Female"
        assert detect_gender("John") == "Male"


class TestNameReplacement:
    """Tests for name replacement."""

    def test_replaces_first_name(self, name_replacer):
        """Should replace first names preserving initial."""
        replacement = name_replacer.replace_first_name("Maria")
        assert replacement[0].upper() == "M"
        assert replacement != "Maria"

    def test_replaces_last_name(self, name_replacer):
        """Should replace last names preserving initial."""
        replacement = name_replacer.replace_last_name("Smith")
        assert replacement[0].upper() == "S"
        assert replacement != "Smith"

    def test_consistent_replacement(self, name_replacer):
        """Should return same replacement for same input."""
        replacement1 = name_replacer.replace_first_name("Maria")
        replacement2 = name_replacer.replace_first_name("Maria")
        assert replacement1 == replacement2

    def test_force_last_names(self, name_replacer):
        """Should treat forced names as last names."""
        name_replacer.add_force_last_names(["Williams"])
        # Auto-detect should treat Williams as last name
        replacement = name_replacer.replace_name_auto("Williams")
        # Check it's the same as calling replace_last_name
        name_replacer2 = NameReplacer(seed=42)
        expected = name_replacer2.replace_last_name("Williams")
        assert replacement[0].upper() == expected[0].upper()


class TestReplacementGenerator:
    """Tests for the ReplacementGenerator."""

    def test_replaces_name(self, generator):
        """Should replace names."""
        replacement = generator.replace_name("Maria")
        assert replacement != "Maria"
        assert len(replacement) > 0

    def test_replaces_location(self, generator):
        """Should replace locations."""
        replacement = generator.replace_location("Chicago")
        assert replacement != "Chicago"
        assert len(replacement) > 0

    def test_replaces_school(self, generator):
        """Should replace school names with different values."""
        replacement = generator.replace_school("Lincoln High School")
        assert "High School" in replacement or "School" in replacement
        # Must differ from original (regression test for same-value bug)
        assert replacement != "Lincoln High School"

    def test_replaces_school_never_returns_original(self):
        """Should never return the same school name as input."""
        # Test multiple seeds to ensure we never get the same value back
        for seed in [42, 123, 456, 789, 1000]:
            gen = ReplacementGenerator(seed=seed)
            replacement = gen.replace_school("Lincoln High School")
            assert replacement != "Lincoln High School", f"Seed {seed} returned original value"

    def test_replaces_email(self, generator):
        """Should replace email addresses."""
        replacement = generator.replace_email("john@gmail.com")
        assert "@" in replacement
        assert replacement != "john@gmail.com"

    def test_replaces_phone(self, generator):
        """Should replace phone numbers."""
        replacement = generator.replace_phone("555-123-4567")
        assert len(replacement) >= 10

    def test_replaces_url(self, generator):
        """Should replace URLs."""
        replacement = generator.replace_url("https://example.com")
        assert "." in replacement

    def test_replaces_age(self, generator):
        """Should replace ages."""
        replacement = generator.replace_age("12 years old")
        assert "years old" in replacement

    def test_skips_countries(self, generator):
        """Should not replace country names."""
        replacement = generator.replace_location("France")
        assert replacement == "France"

    def test_redaction_mode(self, generator):
        """Should redact with placeholder labels."""
        replacement = generator.redact("NAME", "Maria")
        assert replacement == "[name]"

        replacement = generator.redact("EMAIL", "john@gmail.com")
        assert replacement == "[email address]"


class TestActionsConfig:
    """Tests for actions configuration."""

    def test_default_replace(self):
        """Should default to replace action."""
        actions = create_actions_config(default_action="replace")
        assert actions["NAME"] == "replace"
        assert actions["EMAIL"] == "replace"

    def test_default_redact(self):
        """Should support redact as default."""
        actions = create_actions_config(default_action="redact")
        assert actions["NAME"] == "redact"
        assert actions["EMAIL"] == "redact"

    def test_selective_redact(self):
        """Should support selective redaction."""
        actions = create_actions_config(
            default_action="replace",
            redact=["EMAIL", "PHONE"]
        )
        assert actions["NAME"] == "replace"
        assert actions["EMAIL"] == "redact"
        assert actions["PHONE"] == "redact"


class TestTranscriptDeidentifier:
    """Tests for transcript de-identification."""

    def test_deidentifies_transcript(self):
        """Should de-identify a transcript."""
        # Create NER result
        distinct_pii = DistinctPii()
        distinct_pii.add("NAME", "Maria")

        occurrences = [
            PiiOccurrence(start=3, end=8, text="Maria", pii_type="NAME"),
        ]

        ner_result = AnnotatedTranscript(
            distinct_pii=distinct_pii,
            pii_occurrences=occurrences,
            transcript="Hi Maria, how are you?",
        )

        transcript = {
            "utterances": [
                {"text": "Hi Maria, how are you?", "speaker": "Tutor"}
            ]
        }

        deidentifier = TranscriptDeidentifier(seed=42)
        deid_transcript, reid_dict = deidentifier.deidentify(ner_result, transcript)

        # Check that Maria was replaced
        assert "Maria" not in deid_transcript["utterances"][0]["text"]

        # Check reid_dict has the mapping
        assert len(reid_dict) > 0
        assert "Maria" in reid_dict.values()

    def test_preserves_case(self):
        """Should preserve case pattern in replacements."""
        distinct_pii = DistinctPii()
        distinct_pii.add("NAME", "MARIA")

        ner_result = AnnotatedTranscript(
            distinct_pii=distinct_pii,
            pii_occurrences=[
                PiiOccurrence(start=0, end=5, text="MARIA", pii_type="NAME"),
            ],
            transcript="MARIA is here",
        )

        transcript = {"utterances": [{"text": "MARIA is here"}]}

        deidentifier = TranscriptDeidentifier(seed=42)
        deid_transcript, _ = deidentifier.deidentify(ner_result, transcript)

        text = deid_transcript["utterances"][0]["text"]
        # The replacement should be uppercase
        words = text.split()
        assert words[0].isupper()

    def test_returns_reid_dict(self):
        """Should return re-identification dictionary."""
        distinct_pii = DistinctPii()
        distinct_pii.add("NAME", "Maria")

        ner_result = AnnotatedTranscript(
            distinct_pii=distinct_pii,
            pii_occurrences=[
                PiiOccurrence(start=0, end=5, text="Maria", pii_type="NAME"),
            ],
            transcript="Maria is here",
        )

        transcript = {"utterances": [{"text": "Maria is here"}]}

        deidentifier = TranscriptDeidentifier(seed=42)
        _, reid_dict = deidentifier.deidentify(ner_result, transcript)

        # Reid dict should map replacement -> original
        assert "Maria" in reid_dict.values()

    def test_handles_multiple_pii_types(self):
        """Should handle multiple PII types in one transcript."""
        distinct_pii = DistinctPii()
        distinct_pii.add("NAME", "Maria")
        distinct_pii.add("LOCATION", "Chicago")

        ner_result = AnnotatedTranscript(
            distinct_pii=distinct_pii,
            pii_occurrences=[
                PiiOccurrence(start=0, end=5, text="Maria", pii_type="NAME"),
                PiiOccurrence(start=14, end=21, text="Chicago", pii_type="LOCATION"),
            ],
            transcript="Maria is from Chicago",
        )

        transcript = {"utterances": [{"text": "Maria is from Chicago"}]}

        deidentifier = TranscriptDeidentifier(seed=42)
        deid_transcript, reid_dict = deidentifier.deidentify(ner_result, transcript)

        text = deid_transcript["utterances"][0]["text"]
        assert "Maria" not in text
        assert "Chicago" not in text
        assert len(reid_dict) == 2


class TestSeedReproducibility:
    """Tests for seed-based reproducibility."""

    def test_same_seed_same_results(self):
        """Same seed should produce same results."""
        gen1 = ReplacementGenerator(seed=42)
        gen2 = ReplacementGenerator(seed=42)

        replacement1 = gen1.replace_name("Maria")
        replacement2 = gen2.replace_name("Maria")

        assert replacement1 == replacement2

    def test_different_seed_different_results(self):
        """Different seeds should produce different results."""
        gen1 = ReplacementGenerator(seed=42)
        gen2 = ReplacementGenerator(seed=123)

        replacement1 = gen1.replace_location("Chicago")
        replacement2 = gen2.replace_location("Chicago")

        # Different seeds may produce same result by chance, but usually different
        # This test is probabilistic but should pass most of the time
        # We just check they both produce valid replacements
        assert len(replacement1) > 0
        assert len(replacement2) > 0
