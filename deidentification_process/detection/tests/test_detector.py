"""
Tests for the PII Detector.

Covers:
- Name detection (contextual and spaCy)
- Location detection
- School detection
- Date filtering (avoiding false positives)
- Email and URL detection
- Phone number detection
- Age detection
- MISC_ID detection (usernames, SSN)
- False positive filtering
"""

import sys
from pathlib import Path

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from detection.detector import PiiDetector, is_common_first_name
from detection.settings import DetectorSettings


@pytest.fixture
def detector():
    """Create a detector instance for testing."""
    settings = DetectorSettings(model_name="en_core_web_lg")
    return PiiDetector(settings=settings)


class TestNameDetection:
    """Tests for name detection."""

    def test_detects_names_in_greetings(self, detector):
        """Should detect names in greeting patterns."""
        text = "Hi Maria, how are you?"
        result = detector.detect(text)
        assert "Maria" in result.distinct_pii.NAME

    def test_detects_line_initial_names(self, detector):
        """Should detect names at the start of lines."""
        text = "Jayden, can you help me with this problem?"
        result = detector.detect(text)
        assert "Jayden" in result.distinct_pii.NAME

    def test_detects_names_in_self_intro(self, detector):
        """Should detect names in self-introductions."""
        text = "I'm Austin and I need help with math."
        result = detector.detect(text)
        assert "Austin" in result.distinct_pii.NAME

    def test_filters_common_words_as_names(self, detector):
        """Should filter out common words incorrectly detected as names."""
        text = "Everybody should practice this problem."
        result = detector.detect(text)
        assert "Everybody" not in result.distinct_pii.NAME

    def test_filters_interjections(self, detector):
        """Should filter out interjections detected as names."""
        text = "Alrighty, let's start."
        result = detector.detect(text)
        assert "Alrighty" not in result.distinct_pii.NAME

    def test_filters_lowercase_words(self, detector):
        """Should filter out lowercase words (not proper nouns)."""
        text = "The fantastic work is done."
        result = detector.detect(text)
        assert "fantastic" not in result.distinct_pii.NAME


class TestLocationDetection:
    """Tests for location detection."""

    def test_detects_cities(self, detector):
        """Should detect city names."""
        text = "I'm from Chicago and I love it there."
        result = detector.detect(text)
        assert "Chicago" in result.distinct_pii.LOCATION

    def test_filters_math_terms_as_locations(self, detector):
        """Should filter out math terms incorrectly detected as locations."""
        text = "Let's use algebra to solve this."
        result = detector.detect(text)
        assert "algebra" not in result.distinct_pii.LOCATION

    def test_reclassifies_names_from_location(self, detector):
        """Should reclassify common first names from LOCATION to NAME."""
        text = "Alondra is a great student."
        result = detector.detect(text)
        # Alondra might be detected as location but should be reclassified as name
        assert "Alondra" not in result.distinct_pii.LOCATION or "Alondra" in result.distinct_pii.NAME


class TestSchoolDetection:
    """Tests for school detection."""

    def test_detects_school_names(self, detector):
        """Should detect specific school names without intro phrases."""
        text = "I go to Lincoln High School."
        result = detector.detect(text)
        # Should detect exactly "Lincoln High School", not "I go to Lincoln High School"
        assert "Lincoln High School" in result.distinct_pii.SCHOOL
        # Verify intro phrase is NOT included
        assert not any("I go to" in s for s in result.distinct_pii.SCHOOL)

    def test_filters_generic_school_phrases(self, detector):
        """Should filter generic school phrases."""
        text = "I tried this in school yesterday."
        result = detector.detect(text)
        assert "in school" not in [s.lower() for s in result.distinct_pii.SCHOOL]

    def test_filters_school_sentences(self, detector):
        """Should filter sentences that happen to contain 'school'."""
        text = "Do you walk to school every day?"
        result = detector.detect(text)
        assert not result.distinct_pii.SCHOOL or all(
            "walk" not in s.lower() for s in result.distinct_pii.SCHOOL
        )

    def test_school_does_not_absorb_preceding_names(self, detector):
        """Should not absorb names or lowercase words before school name."""
        text = "Hi Maria, I'm Austin from Lincoln High School."
        result = detector.detect(text)
        # Should detect Lincoln High School, not "I'm Austin from Lincoln High School"
        assert "Lincoln High School" in result.distinct_pii.SCHOOL
        assert not any("Austin" in s for s in result.distinct_pii.SCHOOL)
        assert not any("I'm" in s for s in result.distinct_pii.SCHOOL)
        # Austin should be detected as a NAME, not absorbed into SCHOOL
        assert "Austin" in result.distinct_pii.NAME


class TestDateFiltering:
    """Tests for date detection and filtering."""

    def test_filters_relative_time(self, detector):
        """Should filter relative time references."""
        text = "We discussed this yesterday."
        result = detector.detect(text)
        assert "yesterday" not in result.distinct_pii.DATE

    def test_filters_duration_phrases(self, detector):
        """Should filter duration phrases."""
        text = "Wait ten minutes please."
        result = detector.detect(text)
        assert not any("minute" in d.lower() for d in result.distinct_pii.DATE)

    def test_filters_day_names(self, detector):
        """Should filter day names (not specific dates)."""
        text = "Let's meet on Monday."
        result = detector.detect(text)
        assert "Monday" not in result.distinct_pii.DATE


class TestEmailDetection:
    """Tests for email detection."""

    def test_detects_formatted_email(self, detector):
        """Should detect formatted email addresses."""
        text = "Contact me at john.doe@gmail.com please."
        result = detector.detect(text)
        assert "john.doe@gmail.com" in result.distinct_pii.EMAIL

    def test_detects_spoken_email(self, detector):
        """Should detect spoken email patterns."""
        text = "My email is john at gmail dot com"
        result = detector.detect(text)
        assert any("john" in e.lower() and "gmail" in e.lower()
                  for e in result.distinct_pii.EMAIL)


class TestURLDetection:
    """Tests for URL detection."""

    def test_detects_https_url(self, detector):
        """Should detect HTTPS URLs."""
        text = "Visit https://example.com for more info."
        result = detector.detect(text)
        assert any("example.com" in u for u in result.distinct_pii.URL)

    def test_detects_www_url(self, detector):
        """Should detect www URLs."""
        text = "Check out www.example.com today."
        result = detector.detect(text)
        assert any("example.com" in u for u in result.distinct_pii.URL)


class TestPhoneDetection:
    """Tests for phone number detection."""

    def test_detects_formatted_phone(self, detector):
        """Should detect formatted phone numbers."""
        text = "Call me at 555-123-4567 anytime."
        result = detector.detect(text)
        assert "555-123-4567" in result.distinct_pii.PHONE

    def test_filters_phone_in_math_context(self, detector):
        """Should filter phone-like numbers in math context."""
        text = "The equation is 5 plus 5 equals 10."
        result = detector.detect(text)
        # Should not detect math as phone
        assert not result.distinct_pii.PHONE


class TestAgeDetection:
    """Tests for age detection."""

    def test_detects_first_person_age(self, detector):
        """Should detect first-person age without intro phrase."""
        text = "I'm 12 years old."
        result = detector.detect(text)
        # Should detect "12 years old", not "I'm 12 years old"
        assert any("12" in a for a in result.distinct_pii.AGE)
        # Verify intro phrase is NOT included
        assert not any("I'm" in a for a in result.distinct_pii.AGE)

    def test_detects_second_person_age(self, detector):
        """Should detect second-person age without intro phrase."""
        text = "You're 15 years old, right?"
        result = detector.detect(text)
        # Should detect "15 years old", not "You're 15 years old"
        assert any("15" in a for a in result.distinct_pii.AGE)
        # Verify intro phrase is NOT included
        assert not any("You're" in a for a in result.distinct_pii.AGE)


class TestMiscIdDetection:
    """Tests for miscellaneous ID detection."""

    def test_detects_social_handle(self, detector):
        """Should detect social media handles."""
        text = "Follow me @john_doe123 on Twitter."
        result = detector.detect(text)
        assert "@john_doe123" in result.distinct_pii.MISC_ID

    def test_filters_math_variables(self, detector):
        """Should filter single-letter math variables."""
        text = "Solve for x in this equation."
        result = detector.detect(text)
        assert "x" not in result.distinct_pii.MISC_ID


class TestCommonFirstName:
    """Tests for the is_common_first_name helper."""

    def test_recognizes_common_name(self):
        """Should recognize common first names."""
        assert is_common_first_name("Maria") is True
        assert is_common_first_name("John") is True

    def test_rejects_uncommon_words(self):
        """Should reject words that aren't common names."""
        assert is_common_first_name("Algebra") is False
        assert is_common_first_name("x") is False

    def test_handles_empty_input(self):
        """Should handle empty or short input."""
        assert is_common_first_name("") is False
        assert is_common_first_name("A") is False


class TestIntegration:
    """Integration tests for the full detection pipeline."""

    def test_full_transcript_detection(self, detector):
        """Should detect multiple PII types in a full transcript."""
        text = """
Hi Maria, how are you today?
I'm Austin and I go to Lincoln High School.
My email is austin123 at gmail dot com.
Can you help me with math?
"""
        result = detector.detect(text)

        # Should detect names
        assert len(result.distinct_pii.NAME) >= 1

        # Should detect school
        assert any("lincoln" in s.lower() for s in result.distinct_pii.SCHOOL)

        # Should detect email
        assert len(result.distinct_pii.EMAIL) >= 1

    def test_occurrence_positions_are_valid(self, detector):
        """Should have valid occurrence positions."""
        text = "Hi Maria, I'm John from Chicago."
        result = detector.detect(text)

        for occ in result.pii_occurrences:
            # Position should match the text
            assert text[occ.start:occ.end] == occ.text
            # Positions should be within bounds
            assert 0 <= occ.start < len(text)
            assert 0 < occ.end <= len(text)
            assert occ.start < occ.end
