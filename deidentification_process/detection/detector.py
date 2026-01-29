"""
spaCy-based PII Detector for transcript de-identification.

Designed for ASR (Automatic Speech Recognition) transcripts from educational
tutoring sessions. Handles both formatted text and spoken/transcribed patterns.

Key features:
- Line-aware: Each line treated as separate utterance for context detection
- ASR-aware: Detects spoken numbers, emails, URLs
- Educational context filtering: Avoids false positives from math problems
- Bilingual support: Filters Spanish false positives
"""

import re
import sys
from pathlib import Path
from typing import Optional, TypedDict

import spacy
from names_dataset import NameDataset
from spacy.lang.en.stop_words import STOP_WORDS
from spacy.lang.es.stop_words import STOP_WORDS as SPANISH_STOP_WORDS

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared_resources import (
    ALL_PII_TYPES,
    AnnotatedTranscript,
    DistinctPii,
    PiiOccurrence,
    PiiType,
)
from .settings import (
    DetectorSettings,
    DIGIT_WORDS,
    TEEN_WORDS,
    TENS_WORDS,
    STUDENT_AGE_WORDS,
    RELATION_WORDS,
    POSSESSIVE,
    SCHOOL_INDICATORS,
    SCHOOL_INDICATORS_PATTERN,
    MATH_VARIABLE_LETTERS,
    ALL_NUMBER_WORDS,
    FALSE_POSITIVE_NAMES,
    FALSE_POSITIVE_LOCATIONS,
    FALSE_POSITIVE_DATES,
    GENERIC_SCHOOL_PHRASES,
)


class PiiOccurrenceDict(TypedDict):
    """Internal dictionary type for PII occurrences."""
    start: int
    end: int
    text: str
    pii_type: PiiType


# Name dataset singleton
_name_dataset: Optional[NameDataset] = None


def get_name_dataset() -> NameDataset:
    """Get or initialize the NameDataset singleton."""
    global _name_dataset
    if _name_dataset is None:
        _name_dataset = NameDataset()
    return _name_dataset


def is_common_first_name(word: str, min_rank: int = 5000) -> bool:
    """Check if a word is a common first name using the names_dataset.

    Args:
        word: The word to check
        min_rank: Maximum rank to consider "common" (lower = more common)

    Returns:
        True if the word is a common first name
    """
    if not word or len(word) < 2:
        return False

    nd = get_name_dataset()
    result = nd.search(word.capitalize())

    if not result or not result.get("first_name"):
        return False

    ranks = result["first_name"].get("rank", {})
    if not ranks:
        return False

    valid_ranks = [r for r in ranks.values() if r is not None]
    if not valid_ranks:
        return False

    return min(valid_ranks) <= min_rank


class PiiDetector:
    """Detects PII in text using spaCy NER and regex patterns.

    Attributes:
        settings: Detector configuration settings
    """

    # Regex patterns for PII detection (class-level constant)
    PATTERNS: dict[PiiType, list[re.Pattern]] = {
        "PHONE": [
            # Formatted phone numbers
            re.compile(
                r'\b(?:\+?1[-.\s]?)?'
                r'(?:\(?\d{3}\)?[-.\s]?)?'
                r'\d{3}[-.\s]?\d{4}\b'
            ),
            # ASR: Spoken phone numbers
            re.compile(
                rf'\b(?:(?:my\s+)?(?:phone\s+)?(?:number\s+)?(?:is\s+)?)?'
                rf'(?:{DIGIT_WORDS}\s*[-,]?\s*){{7,11}}\b',
                re.IGNORECASE
            ),
            # ASR: Area code pattern
            re.compile(
                rf'\barea\s+code\s+(?:{DIGIT_WORDS}\s*){{3}}\b',
                re.IGNORECASE
            ),
        ],
        "EMAIL": [
            # Formatted email
            re.compile(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ),
            # ASR: Spoken email
            re.compile(
                r'\b[\w.-]+\s+at\s+[\w.-]+\s+dot\s+(?:com|org|net|edu|gov|io|co)\b',
                re.IGNORECASE
            ),
            # ASR: Known domains
            re.compile(
                r'\b(?:email\s+(?:is\s+)?)?[\w.-]+\s+at\s+'
                r'(?:gmail|yahoo|hotmail|outlook|aol|icloud|proton\s*mail)'
                r'(?:\s+dot\s+com)?\b',
                re.IGNORECASE
            ),
        ],
        "URL": [
            # Formatted URL
            re.compile(r'\b(?:https?://|www\.)[^\s<>\"{}|\\^`\[\]]+\b'),
            # ASR: Spoken URL
            re.compile(
                r'\b(?:(?:w\s+w\s+w|triple\s+w|dub\s+dub\s+dub|'
                r'double[-\s]?(?:u|you)\s+double[-\s]?(?:u|you)\s+double[-\s]?(?:u|you)|'
                r'dubya\s+dubya\s+dubya)\s+dot\s+)?'
                r'[\w-]+\s+dot\s+(?:com|org|net|edu|gov|io|co)(?:\s+slash\s+[\w-]+)*\b',
                re.IGNORECASE
            ),
        ],
        "DATE": [
            # Month DD, YYYY (e.g., "March 15, 2024" or "March 15th, 2024")
            re.compile(
                r'\b(?:January|February|March|April|May|June|July|August|September|'
                r'October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b',
                re.IGNORECASE
            ),
            # DD Month YYYY (e.g., "15 March 2024" or "15th of March, 2024")
            re.compile(
                r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?'
                r'(?:January|February|March|April|May|June|July|August|September|'
                r'October|November|December),?\s+\d{4}\b',
                re.IGNORECASE
            ),
            # MM/DD/YYYY or MM-DD-YYYY
            re.compile(r'\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-]\d{4}\b'),
            # YYYY-MM-DD (ISO format)
            re.compile(r'\b\d{4}-(?:0?[1-9]|1[0-2])-(?:0?[1-9]|[12]\d|3[01])\b'),
            # Month YYYY (e.g., "March 2024")
            re.compile(
                r'\b(?:January|February|March|April|May|June|July|August|September|'
                r'October|November|December)\s+\d{4}\b',
                re.IGNORECASE
            ),
        ],
        "AGE": [
            # First person: "I'm 12" -> captures "12 years old" (group 1)
            re.compile(
                r'\b(?:i\'?m|i am|my age is)\s+'
                r'((1[0-9]|[1-9])\s*(?:years?\s*old|y/?o)?)\b',
                re.IGNORECASE
            ),
            # First person spoken: "I'm twelve" -> captures "twelve years old" (group 1)
            re.compile(
                rf'\b(?:i\'?m|i am|my age is)\s+'
                rf'({STUDENT_AGE_WORDS}'
                rf'(?:\s+years?\s+old)?)\b',
                re.IGNORECASE
            ),
            # Second person: "you're 12" -> captures "12 years old" (group 1)
            re.compile(
                r'\b(?:you\'?re|you are)\s+'
                r'((1[0-9]|[1-9])\s*(?:years?\s*old|y/?o)?)\b',
                re.IGNORECASE
            ),
            # Third person with pronoun -> captures age phrase (group 1)
            re.compile(
                r'\b(?:he|she|they)(?:\'s|\s+(?:is|are))\s+'
                r'((1[0-9]|[1-9])\s*(?:years?\s*old|y/?o)?)\b',
                re.IGNORECASE
            ),
            # Third person with possessive + relation -> captures age phrase (group 1)
            re.compile(
                rf'\b{POSSESSIVE}\s+{RELATION_WORDS}\s+(?:is|are)\s+'
                rf'((1[0-9]|[1-9])\s*(?:years?\s*old|y/?o)?)\b',
                re.IGNORECASE
            ),
        ],
        "MISC_ID": [
            # Formatted SSN
            re.compile(r'\b(?:\d{3}-\d{2}-\d{4}|\d{9}|[A-Z]{2}\d{6,8})\b'),
            # Social media handles
            re.compile(r'@[a-zA-Z_][\w]{2,30}\b'),
            # Usernames in context
            re.compile(
                r'\b(?:my\s+)?(?:username|user\s*name|screen\s*name|gamer\s*tag|handle|'
                r'(?:discord|twitch|roblox|minecraft|fortnite|tiktok|instagram|snapchat|twitter|x)\s*'
                r'(?:name|handle|username|user|is)?)\s+'
                r'(?:is\s+)?["\']?[\w._-]{3,25}["\']?\b',
                re.IGNORECASE
            ),
        ],
        "SCHOOL": [
            # Direct school mentions
            re.compile(
                rf'\b(?:'
                rf'i\s+(?:go|went|attend|attended)\s+to|'
                rf'i\'?m\s+(?:at|from|a\s+student\s+at)|'
                rf'(?:my|our)\s+school\s+is|'
                rf'study(?:ing)?\s+at|'
                rf'enrolled\s+(?:at|in)|'
                rf'you(?:\'re|\s+are)\s+(?:at|from|a\s+student\s+at)|'
                rf'you\s+(?:go|went|attend|attended)\s+to|'
                rf'(?:your|y\'?all\'?s?)\s+school\s+is'
                rf')\s+([A-Z][a-zA-Z\s\'\.]+?{SCHOOL_INDICATORS_PATTERN})\b',
                re.IGNORECASE
            ),
            # School names with suffixes (word prefix must be capitalized, indicators case-insensitive)
            re.compile(
                rf'\b((?:[A-Z][a-zA-Z\'\.]*\s+){{1,4}}(?i:{SCHOOL_INDICATORS_PATTERN}))\b'
            ),
            # Abbreviated school patterns
            re.compile(
                r'\b(?:P\.?S\.?|I\.?S\.?|M\.?S\.?|J\.?H\.?S\.?|H\.?S\.?)\s*#?\d{1,4}\b',
                re.IGNORECASE
            ),
        ],
    }

    # spaCy entity labels mapped to PII types
    SPACY_LABEL_MAP: dict[str, PiiType] = {
        "PERSON": "NAME",
        "GPE": "LOCATION",
        "LOC": "LOCATION",
        "FAC": "LOCATION",
        "ORG": "LOCATION",
        "DATE": "DATE",
        "TIME": "DATE",
    }

    def __init__(self, settings: Optional[DetectorSettings] = None):
        """Initialize the PII detector.

        Args:
            settings: Detector configuration settings. Uses defaults if not provided.
        """
        self.settings = settings or DetectorSettings()
        try:
            self._nlp = spacy.load(self.settings.model_name)
        except OSError:
            spacy.cli.download(self.settings.model_name)
            self._nlp = spacy.load(self.settings.model_name)

    def _filter_false_positives(
        self, text: str, pii_type: PiiType, start: int, end: int
    ) -> bool:
        """Filter out common false positives.

        Args:
            text: The matched text
            pii_type: Type of PII
            start: Start position in document
            end: End position in document

        Returns:
            True if the match should be kept, False if it's a false positive
        """
        text_lower = text.lower().strip()

        if pii_type == "NAME":
            if text_lower in FALSE_POSITIVE_NAMES | SPANISH_STOP_WORDS:
                return False
            if " " in text_lower or "\n" in text:
                return False
            if len(text) <= 2:
                return False
            if text.islower():
                return False

        elif pii_type == "LOCATION":
            if text_lower in FALSE_POSITIVE_LOCATIONS:
                return False
            if len(text) <= 3 and not text.isupper():
                return False
            fp_patterns = [
                "the four", "comes first", "four friends",
                "my mouth", "white board", "whiteboard",
                "big boss", "checkmate",
            ]
            if any(p in text_lower for p in fp_patterns):
                return False

        elif pii_type == "DATE":
            if text_lower in FALSE_POSITIVE_DATES:
                return False
            fp_patterns = [
                "few minutes", "couple minutes", "about an hour",
                "several weeks", "this year", "last year", "next year",
                "extra minute", "one month", "one year",
            ]
            if any(p in text_lower for p in fp_patterns):
                return False
            # Filter pure numeric strings but allow formatted dates (with - or /)
            if text_lower.replace(" ", "").isdigit():
                return False
            # Duration words at end (e.g., "five years", "ten minutes")
            duration_words = ["years", "year", "months", "month", "weeks", "week",
                            "days", "day", "hours", "hour", "minutes", "minute",
                            "seconds", "second"]
            if any(text_lower.endswith(d) for d in duration_words):
                return False
            # Number word + time unit patterns (e.g., "ten minutes")
            time_units = ["minute", "hour", "second", "day", "week", "month", "year"]
            for unit in time_units:
                if unit in text_lower or f"{unit}s" in text_lower:
                    # Check if it starts with a number word
                    for num_word in ALL_NUMBER_WORDS:
                        if text_lower.startswith(num_word):
                            return False

        elif pii_type == "SCHOOL":
            if "\n" in text:
                return False
            words = text.split()
            if words and not words[0][0].isupper():
                return False
            if text_lower in GENERIC_SCHOOL_PHRASES:
                return False
            sentence_patterns = [
                "in school", "to school", "at school", "from school",
                "this in school", "walk to school", "go to school",
            ]
            if any(p in text_lower for p in sentence_patterns):
                return False

        elif pii_type == "MISC_ID":
            if text_lower in MATH_VARIABLE_LETTERS:
                return False
            if text.startswith("@") and text[1:].lower() in MATH_VARIABLE_LETTERS:
                return False

        return True

    def _detect_contextual_names(
        self, text: str, doc: "spacy.tokens.Doc"
    ) -> list[PiiOccurrenceDict]:
        """Detect names using conversational context patterns.

        Args:
            text: The transcript text
            doc: spaCy Doc object

        Returns:
            List of detected name occurrences
        """
        occurrences: list[PiiOccurrenceDict] = []
        non_name_pos_prefixes = ("VB", "JJ", "RB")

        false_positives = STOP_WORDS | SPANISH_STOP_WORDS | {
            "ok", "okay", "yeah", "yep", "nope", "alright", "hey", "hi", "hello", "bye",
            "mm", "hmm", "hm", "mhm", "uh-huh", "nah", "yay", "ooh", "oof", "whoa",
            "wow", "oh", "ah", "um", "uh", "sorry", "thanks", "please",
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
            "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
            "first", "second", "third", "fourth", "fifth", "last", "next",
            "boy", "girl", "man", "woman", "guys", "boys", "girls", "people", "kids",
            "cool", "awesome", "amazing", "perfect", "exactly", "correct", "true", "false",
            "like", "thank", "sir", "teacher", "tutor",
        }

        patterns: list[tuple[re.Pattern[str], str]] = [
            # Line-initial names
            (
                re.compile(
                    r'^([A-Z][a-z]+)(?:,|\.|!|\?|(?:\s+(?:can|could|would|do|are|is|how|what|where|why|come|look|wait|stop|go|please)))',
                    re.MULTILINE
                ),
                "line_initial"
            ),
            # Line-final names
            (re.compile(r',\s+([A-Z][a-z]+)[.!?]?$', re.MULTILINE), "line_final"),
            # Self-intro
            (re.compile(r'^(?:I\'?m|I am)\s+([A-Z][a-z]+)', re.MULTILINE), "self_intro"),
            # Greetings
            (
                re.compile(
                    r'\b(?:hi|hello|hey|thanks|thank you|bye|goodbye|'
                    r'good (?:morning|afternoon|evening|night)|'
                    r'see you(?: later)?|nice to meet you),?\s+([A-Z][a-z]+)\b',
                    re.IGNORECASE
                ),
                "greeting"
            ),
            # Affirmations
            (
                re.compile(
                    r'\b(?:good (?:job|work)|alright|all right|okay|ok),?\s+([A-Z][a-z]+)[.!?,]?\b',
                    re.IGNORECASE
                ),
                "affirmation"
            ),
        ]

        seen_spans: set[tuple[int, int]] = set()

        for pattern, pattern_type in patterns:
            for match in pattern.finditer(text):
                name = match.group(1)
                if not name or name.lower() in false_positives:
                    continue

                match_text = match.group(0)
                name_offset = match_text.lower().rfind(name.lower())
                if name_offset == -1:
                    name_offset = match_text.find(name)
                name_start = match.start() + name_offset
                name_end = name_start + len(name)
                span = (name_start, name_end)

                if any(not (span[1] <= s[0] or span[0] >= s[1]) for s in seen_spans):
                    continue

                token_span = doc.char_span(name_start, name_end)
                if token_span is not None and len(token_span) == 1:
                    token = token_span[0]
                    if token.tag_.startswith(non_name_pos_prefixes):
                        continue

                seen_spans.add(span)
                occurrences.append({
                    "start": name_start,
                    "end": name_end,
                    "text": name,
                    "pii_type": "NAME"
                })

        return occurrences

    def _is_math_context(self, text: str, start: int, end: int) -> bool:
        """Check if a span appears in a math problem context."""
        context_start = max(0, start - 100)
        context_end = min(len(text), end + 100)
        context = text[context_start:context_end].lower()

        math_indicators = [
            "plus", "minus", "times", "divided", "equals", "multiply", "subtract", "add",
            "equation", "problem", "calculate", "solve", "answer", "sum", "product",
            "number line", "fraction", "decimal", "percent", "negative", "positive",
        ]

        span_text = text[start:end].lower()
        word_count = sum(1 for w in ALL_NUMBER_WORDS if w in span_text)
        if word_count >= 5:
            return True

        return any(indicator in context for indicator in math_indicators)

    def detect(self, text: str) -> AnnotatedTranscript:
        """Detect PII in the given text.

        Args:
            text: The transcript text to analyze

        Returns:
            AnnotatedTranscript with detected PII
        """
        doc = self._nlp(text)
        occurrences: list[PiiOccurrenceDict] = []
        seen_spans: set[tuple[int, int]] = set()

        # 1. Detect regex patterns first (before spaCy NER)
        # EMAIL must come before MISC_ID (social handles) to avoid @gmail being caught as handle
        regex_priority_types: list[PiiType] = ["EMAIL", "PHONE", "URL", "DATE", "AGE", "SCHOOL", "MISC_ID"]
        for pii_type in regex_priority_types:
            if pii_type not in self.PATTERNS:
                continue
            for pattern in self.PATTERNS[pii_type]:
                for match in pattern.finditer(text):
                    # Use capture group if available (for SCHOOL/AGE patterns that
                    # have intro phrases we want to exclude)
                    if match.lastindex and match.lastindex >= 1:
                        matched_text = match.group(1)
                        span = (match.start(1), match.end(1))
                    else:
                        matched_text = match.group(0)
                        span = (match.start(), match.end())

                    overlaps = any(
                        not (span[1] <= existing[0] or span[0] >= existing[1])
                        for existing in seen_spans
                    )

                    if not overlaps and self._filter_false_positives(
                        matched_text, pii_type, span[0], span[1]
                    ):
                        if pii_type == "PHONE" and self._is_math_context(text, span[0], span[1]):
                            continue

                        seen_spans.add(span)
                        occurrences.append({
                            "start": span[0],
                            "end": span[1],
                            "text": matched_text,
                            "pii_type": pii_type
                        })

        # 2. Detect contextual names
        if self.settings.enable_contextual_names:
            for occ in self._detect_contextual_names(text, doc):
                span = (occ["start"], occ["end"])
                overlaps = any(
                    not (span[1] <= existing[0] or span[0] >= existing[1])
                    for existing in seen_spans
                )
                if not overlaps and self._filter_false_positives(occ["text"], "NAME", span[0], span[1]):
                    seen_spans.add(span)
                    occurrences.append(occ)

        # 3. Detect PII using spaCy NER
        for ent in doc.ents:
            if ent.label_ in self.SPACY_LABEL_MAP:
                pii_type = self.SPACY_LABEL_MAP[ent.label_]
                span = (ent.start_char, ent.end_char)

                # Reclassify ORG entities that look like schools
                if ent.label_ == "ORG":
                    ent_lower = ent.text.lower()
                    if any(indicator in ent_lower for indicator in SCHOOL_INDICATORS):
                        pii_type = "SCHOOL"

                overlaps = any(
                    not (span[1] <= existing[0] or span[0] >= existing[1])
                    for existing in seen_spans
                )

                if not overlaps and self._filter_false_positives(
                    ent.text, pii_type, ent.start_char, ent.end_char
                ):
                    seen_spans.add(span)
                    occurrences.append({
                        "start": ent.start_char,
                        "end": ent.end_char,
                        "text": ent.text,
                        "pii_type": pii_type
                    })

        # Sort by position
        occurrences.sort(key=lambda x: x["start"])

        # 4. Post-processing: Reclassify LOCATION -> NAME for common names
        for occ in occurrences:
            if occ["pii_type"] == "LOCATION":
                text_val = occ["text"]
                if " " not in text_val and is_common_first_name(
                    text_val, self.settings.min_name_rank
                ):
                    occ["pii_type"] = "NAME"

        # Build distinct PII
        distinct_pii = DistinctPii()
        seen_content: dict[PiiType, set[str]] = {t: set() for t in ALL_PII_TYPES}

        for occ in occurrences:
            pii_type = occ["pii_type"]
            content_key = occ["text"].lower()
            if content_key not in seen_content[pii_type]:
                seen_content[pii_type].add(content_key)
                distinct_pii.add(pii_type, occ["text"])

        # Convert to Pydantic models
        pii_occurrences = [
            PiiOccurrence(
                start=occ["start"],
                end=occ["end"],
                text=occ["text"],
                pii_type=occ["pii_type"],
            )
            for occ in occurrences
        ]

        return AnnotatedTranscript(
            distinct_pii=distinct_pii,
            pii_occurrences=pii_occurrences,
            transcript=text,
        )

    def detect_file(self, filepath: str) -> AnnotatedTranscript:
        """Load a transcript file and detect PII.

        Args:
            filepath: Path to the transcript file

        Returns:
            AnnotatedTranscript with detected PII
        """
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        return self.detect(text)
