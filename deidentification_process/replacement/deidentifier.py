"""
Transcript De-identification Module.

Applies PII replacements to transcript JSON structures using detected PII
from an AnnotatedTranscript.

Supports two replacement strategies:
- Global: Replace all occurrences of PII text (word-boundary aware, case-sensitive)
- Position-only: Replace only at detected positions (for numeric types that
  might appear in math context)
"""

import copy
import re
import sys
from pathlib import Path
from typing import Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared_resources import (
    AnnotatedTranscript,
    PiiOccurrence,
    PiiType,
    ALL_PII_TYPES,
)
from shared_resources.constants import (
    DeidentifyAction,
    GLOBAL_REPLACE_CATEGORIES,
    POSITION_ONLY_CATEGORIES,
    TITLE_PREFIXES,
)
from .replacement_generator import (
    ReplacementGenerator,
    create_replacement_generator,
    create_actions_config,
)


def _match_case(original: str, replacement: str) -> str:
    """Match the case pattern of the original text in the replacement.

    Args:
        original: Original text with case pattern
        replacement: Replacement text to adjust

    Returns:
        Replacement with matched case pattern
    """
    if original.isupper():
        return replacement.upper()
    elif original.islower():
        return replacement.lower()
    elif original.istitle():
        # Title Case Like This -> preserve title case
        return replacement.title()
    elif original and original[0].isupper():
        return replacement.capitalize()
    return replacement


class TranscriptDeidentifier:
    """De-identifies transcript JSON using detected PII from NER.

    Handles two replacement strategies:
    - Global replacement for names, locations, schools, dates, emails, URLs
    - Position-only replacement for ages, phones, IDs (to preserve math context)
    """

    # Fields to skip during de-identification
    SKIP_FIELDS: set[str] = {"start", "end", "speaker_type"}

    def __init__(
        self,
        generator: Optional[ReplacementGenerator] = None,
        locale: str = "en_US",
        seed: Optional[int] = None,
    ):
        """Initialize the deidentifier.

        Args:
            generator: Optional ReplacementGenerator instance
            locale: Faker locale for replacement generation
            seed: Random seed for reproducible replacements
        """
        self.generator = generator or create_replacement_generator(locale=locale, seed=seed)

    def _detect_names_after_titles(
        self,
        text: str,
        names: list[str],
    ) -> tuple[set[str], dict[str, str]]:
        """Detect which names appear after title prefixes.

        Args:
            text: The transcript text
            names: List of detected names

        Returns:
            Tuple of (surnames, compound_name_mappings)
        """
        surnames = set()
        compound_to_name: dict[str, str] = {}
        text_lower = text.lower()

        for name in names:
            name_lower = name.lower()
            name_parts = name.split()

            if len(name_parts) >= 2:
                first_word = name_parts[0].rstrip(".")
                if first_word.lower() in TITLE_PREFIXES:
                    name_only = " ".join(name_parts[1:])
                    compound_to_name[name] = name_only
                    surnames.add(name_only)
                    continue

            name_escaped = re.escape(name)
            for title in TITLE_PREFIXES:
                title_escaped = re.escape(title)
                pattern = rf'\b{title_escaped}\s*[.\s]*{name_escaped}\b'
                if re.search(pattern, text_lower, re.IGNORECASE):
                    surnames.add(name)
                    break

        return surnames, compound_to_name

    def _build_line_index(self, text: str) -> list[tuple[int, int]]:
        """Build index mapping line numbers to character positions."""
        lines = text.split("\n")
        index = []
        pos = 0
        for line in lines:
            index.append((pos, pos + len(line)))
            pos += len(line) + 1
        return index

    def _map_occurrence_to_utterance(
        self,
        occ: PiiOccurrence,
        line_index: list[tuple[int, int]],
        utterances: list[dict[str, Any]],
    ) -> tuple[int, int, int] | None:
        """Map a PII occurrence to its position in an utterance."""
        for line_num, (line_start, line_end) in enumerate(line_index):
            if line_start <= occ.start < line_end:
                if line_num >= len(utterances):
                    return None

                pos_in_line = occ.start - line_start
                end_in_line = occ.end - line_start

                utt_text = utterances[line_num].get("text", "")
                if pos_in_line < len(utt_text) and utt_text[pos_in_line:end_in_line] == occ.text:
                    return (line_num, pos_in_line, end_in_line)

                return None

        return None

    def _escape_for_regex(self, text: str) -> str:
        """Escape special regex characters in text."""
        return re.escape(text)

    def _apply_global_replacements(
        self,
        utterances: list[dict[str, Any]],
        replacements: dict[str, str],
    ) -> None:
        """Apply global replacements using word boundaries.

        Args:
            utterances: List of utterance dicts (modified in place)
            replacements: Dict of original -> replacement
        """
        sorted_replacements = sorted(
            replacements.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )

        for i, utt in enumerate(utterances):
            for field_name, field_value in list(utt.items()):
                if field_name in self.SKIP_FIELDS:
                    continue
                if not isinstance(field_value, str):
                    continue

                text = field_value
                for original, replacement in sorted_replacements:
                    pattern = r'\b' + self._escape_for_regex(original) + r'\b'

                    def make_replacement(match: re.Match, repl: str = replacement) -> str:
                        return _match_case(match.group(0), repl)

                    text = re.sub(pattern, make_replacement, text, flags=re.IGNORECASE)

                utterances[i][field_name] = text

    def _apply_position_replacements(
        self,
        utterances: list[dict[str, Any]],
        occurrences: list[PiiOccurrence],
        line_index: list[tuple[int, int]],
        replacements: dict[str, str],
    ) -> None:
        """Apply replacements only at detected positions.

        Args:
            utterances: List of utterance dicts (modified in place)
            occurrences: List of PII occurrences
            line_index: Line index for position mapping
            replacements: Dict of original -> replacement
        """
        utterance_occurrences: dict[int, list[tuple[int, int, str, str]]] = {}

        for occ in occurrences:
            if occ.text not in replacements:
                continue

            pos = self._map_occurrence_to_utterance(occ, line_index, utterances)
            if pos is None:
                continue

            utt_idx, start, end = pos
            if utt_idx not in utterance_occurrences:
                utterance_occurrences[utt_idx] = []

            utterance_occurrences[utt_idx].append(
                (start, end, occ.text, replacements[occ.text])
            )

        for utt_idx, occ_list in utterance_occurrences.items():
            occ_list.sort(key=lambda x: x[0], reverse=True)

            text = utterances[utt_idx].get("text", "")

            for start, end, original, replacement in occ_list:
                text = text[:start] + replacement + text[end:]

            utterances[utt_idx]["text"] = text

    def deidentify(
        self,
        ner_result: AnnotatedTranscript,
        transcript: dict[str, Any],
        actions: Optional[dict[PiiType, DeidentifyAction]] = None,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """De-identify a transcript using detected PII.

        Args:
            ner_result: AnnotatedTranscript from NER detection
            transcript: Transcript dict with 'utterances' array
            actions: Optional dict mapping PII type to action

        Returns:
            (de-identified transcript, re-identification dict)
        """
        if actions is None:
            actions = {pii_type: "replace" for pii_type in ALL_PII_TYPES}

        deid_transcript = copy.deepcopy(transcript)
        utterances = deid_transcript.get("utterances", [])

        line_index = self._build_line_index(ner_result.transcript)

        detected_names = getattr(ner_result.distinct_pii, "NAME", [])
        surnames, compound_names = self._detect_names_after_titles(
            ner_result.transcript, detected_names
        )
        if surnames:
            self.generator.add_force_last_names(list(surnames))

        self._compound_names = compound_names

        all_replacements: dict[str, str] = {}
        reid_dict: dict[str, str] = {}

        global_replacements: dict[str, str] = {}

        for pii_type in GLOBAL_REPLACE_CATEGORIES:
            items = getattr(ner_result.distinct_pii, pii_type, [])
            action = actions.get(pii_type, "replace")

            for item in items:
                if item in all_replacements:
                    continue

                if pii_type == "NAME" and item in compound_names:
                    name_only = compound_names[item]
                    name_replacement = self.generator.deidentify("NAME", name_only, action)
                    title_part = item[:item.lower().find(name_only.lower())].rstrip()
                    replacement = f"{title_part} {name_replacement}"

                    if name_only not in all_replacements:
                        all_replacements[name_only] = name_replacement
                        global_replacements[name_only] = name_replacement
                        reid_dict[name_replacement] = name_only
                else:
                    replacement = self.generator.deidentify(pii_type, item, action)

                all_replacements[item] = replacement
                global_replacements[item] = replacement
                reid_dict[replacement] = item

        position_replacements: dict[str, str] = {}
        position_occurrences: list[PiiOccurrence] = []

        for pii_type in POSITION_ONLY_CATEGORIES:
            items = getattr(ner_result.distinct_pii, pii_type, [])
            action = actions.get(pii_type, "replace")

            for item in items:
                if item in all_replacements:
                    continue

                replacement = self.generator.deidentify(pii_type, item, action)
                all_replacements[item] = replacement
                position_replacements[item] = replacement
                reid_dict[replacement] = item

        for occ in ner_result.pii_occurrences:
            if occ.pii_type in POSITION_ONLY_CATEGORIES:
                position_occurrences.append(occ)

        self._apply_position_replacements(
            utterances, position_occurrences, line_index, position_replacements
        )

        self._apply_global_replacements(utterances, global_replacements)

        return deid_transcript, reid_dict


def deidentify_transcript(
    ner_result: AnnotatedTranscript,
    transcript: dict[str, Any],
    actions: Optional[dict[PiiType, DeidentifyAction]] = None,
    locale: str = "en_US",
    seed: Optional[int] = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Convenience function to de-identify a transcript.

    Args:
        ner_result: AnnotatedTranscript from NER detection
        transcript: Transcript dict with 'utterances' array
        actions: Optional dict mapping PII type to action
        locale: Faker locale for replacement generation
        seed: Random seed for reproducible replacements

    Returns:
        (de-identified transcript, re-identification dict)
    """
    deidentifier = TranscriptDeidentifier(locale=locale, seed=seed)
    return deidentifier.deidentify(ner_result, transcript, actions)
