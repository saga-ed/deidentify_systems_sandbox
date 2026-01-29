"""
Pydantic schemas for PII detection and transcript de-identification.

These schemas define the data structures used throughout the de-identification
pipeline, from raw transcript input to annotated output.

Schema Hierarchy:
    Transcript (input) -> AnnotatedTranscript (after NER) -> De-identified Transcript (output)

PII Categories (aligned with FERPA, COPPA, and HIPAA requirements):
    - NAME: Person names (first names, last names, full names)
    - LOCATION: Geographic locations (cities, states, countries, addresses)
    - SCHOOL: Educational institutions (schools, universities, academies)
    - DATE: Specific dates (birth dates, enrollment dates)
    - AGE: Participant ages
    - PHONE: Phone numbers
    - EMAIL: Email addresses
    - URL: Web addresses
    - MISC_ID: Other identifiers (SSN, student IDs, usernames)
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# Type definitions
PiiType = Literal[
    "NAME",
    "LOCATION",
    "SCHOOL",
    "DATE",
    "AGE",
    "PHONE",
    "EMAIL",
    "URL",
    "MISC_ID",
]

# All PII types as a list (for iteration)
ALL_PII_TYPES: list[PiiType] = [
    "NAME",
    "LOCATION",
    "SCHOOL",
    "DATE",
    "AGE",
    "PHONE",
    "EMAIL",
    "URL",
    "MISC_ID",
]


class PiiOccurrence(BaseModel):
    """A single occurrence of PII in the transcript.

    Attributes:
        start: Start character index in the transcript text
        end: End character index in the transcript text
        text: The matched PII text
        pii_type: Category of PII (NAME, LOCATION, etc.)
    """

    start: int = Field(..., description="Start character index in transcript")
    end: int = Field(..., description="End character index in transcript")
    text: str = Field(..., description="The matched text")
    pii_type: PiiType = Field(..., description="Category of PII")


class DistinctPii(BaseModel):
    """Distinct PII items grouped by type.

    Each list contains unique PII values found in the transcript.
    The lists are deduplicated (case-insensitive).

    Example:
        {
            "NAME": ["John", "Maria"],
            "LOCATION": ["Chicago"],
            "SCHOOL": ["Lincoln High School"],
            ...
        }
    """

    NAME: list[str] = Field(default_factory=list)
    LOCATION: list[str] = Field(default_factory=list)
    SCHOOL: list[str] = Field(default_factory=list)
    DATE: list[str] = Field(default_factory=list)
    AGE: list[str] = Field(default_factory=list)
    PHONE: list[str] = Field(default_factory=list)
    EMAIL: list[str] = Field(default_factory=list)
    URL: list[str] = Field(default_factory=list)
    MISC_ID: list[str] = Field(default_factory=list)

    def add(self, pii_type: PiiType, content: str) -> None:
        """Add a PII item to the appropriate category if not already present.

        Deduplication is case-insensitive: "Maria" and "MARIA" are considered
        the same item, and only the first occurrence is kept.

        Args:
            pii_type: The category of PII (NAME, LOCATION, etc.)
            content: The PII value to add
        """
        items = getattr(self, pii_type)
        # Case-insensitive deduplication
        if not any(item.lower() == content.lower() for item in items):
            items.append(content)

    def get(self, pii_type: PiiType) -> list[str]:
        """Get items for a specific PII type.

        Args:
            pii_type: The category of PII

        Returns:
            List of PII values for the specified type
        """
        return getattr(self, pii_type)

    def to_dict(self) -> dict[PiiType, list[str]]:
        """Convert to dictionary format.

        Returns:
            Dict mapping PII type to list of values
        """
        return {
            "NAME": self.NAME,
            "LOCATION": self.LOCATION,
            "SCHOOL": self.SCHOOL,
            "DATE": self.DATE,
            "AGE": self.AGE,
            "PHONE": self.PHONE,
            "EMAIL": self.EMAIL,
            "URL": self.URL,
            "MISC_ID": self.MISC_ID,
        }

    def count(self) -> int:
        """Return total count of distinct PII items across all categories."""
        return sum(len(getattr(self, pii_type)) for pii_type in ALL_PII_TYPES)


class AnnotatedTranscript(BaseModel):
    """A transcript with detected PII annotations.

    This is the output of the detection phase and the input to the
    replacement phase.

    Attributes:
        distinct_pii: Unique PII items grouped by type
        pii_occurrences: All PII occurrences with their positions
        transcript: The original transcript text (newline-separated utterances)
    """

    distinct_pii: DistinctPii = Field(
        default_factory=DistinctPii,
        description="Distinct PII items grouped by type"
    )
    pii_occurrences: list[PiiOccurrence] = Field(
        default_factory=list,
        description="All PII occurrences with positions"
    )
    transcript: str = Field(..., description="The original transcript text")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "distinct_pii": {
                    "NAME": ["Austin", "Maria"],
                    "LOCATION": ["Chicago"],
                    "SCHOOL": ["Lincoln High School"],
                    "DATE": [],
                    "AGE": [],
                    "PHONE": [],
                    "EMAIL": [],
                    "URL": [],
                    "MISC_ID": [],
                },
                "pii_occurrences": [
                    {"start": 0, "end": 6, "text": "Austin", "pii_type": "NAME"},
                    {"start": 45, "end": 52, "text": "Chicago", "pii_type": "LOCATION"},
                ],
                "transcript": "Austin is from Chicago..."
            }
        }
    )


class Utterance(BaseModel):
    """A single utterance (speaker turn) in a transcript.

    Represents one line/segment of speech from a single speaker.

    Attributes:
        text: The spoken text
        speaker: Speaker identifier (e.g., "Tutor", "Student")
        speaker_type: Type of speaker (e.g., "tutor", "student")
        start: Start time in seconds (optional, for audio-aligned transcripts)
        end: End time in seconds (optional, for audio-aligned transcripts)
    """

    text: str = Field(..., description="The spoken text")
    speaker: Optional[str] = Field(None, description="Speaker identifier")
    speaker_type: Optional[str] = Field(None, description="Type of speaker")
    start: Optional[float] = Field(None, description="Start time in seconds")
    end: Optional[float] = Field(None, description="End time in seconds")


class Transcript(BaseModel):
    """A complete transcript with utterances and optional metadata.

    This is the standard input format for the de-identification pipeline.

    Attributes:
        utterances: List of utterances in chronological order
        session_id: Optional session identifier
        metadata: Optional additional metadata
    """

    utterances: list[Utterance] = Field(
        default_factory=list,
        description="List of utterances in chronological order"
    )
    session_id: Optional[str] = Field(None, description="Session identifier")
    metadata: Optional[dict] = Field(None, description="Additional metadata")

    def to_text(self) -> str:
        """Convert transcript to newline-separated text.

        Returns:
            String with each utterance on a separate line
        """
        return "\n".join(utt.text for utt in self.utterances)

    @classmethod
    def from_dict(cls, data: dict) -> "Transcript":
        """Create Transcript from a dictionary.

        Handles both 'segments' and 'utterances' keys for compatibility.

        Args:
            data: Dictionary with transcript data

        Returns:
            Transcript instance
        """
        utterances = []
        source_key = "utterances" if "utterances" in data else "segments"

        for item in data.get(source_key, []):
            utterances.append(Utterance(
                text=item.get("text", ""),
                speaker=item.get("speaker"),
                speaker_type=item.get("speaker_type"),
                start=item.get("start"),
                end=item.get("end"),
            ))

        return cls(
            utterances=utterances,
            session_id=data.get("session_id"),
            metadata={k: v for k, v in data.items()
                     if k not in ("utterances", "segments", "session_id")}
        )
