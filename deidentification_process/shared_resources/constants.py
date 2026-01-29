"""
Shared constants for the de-identification pipeline.

Contains configuration values, priority orderings, and labels used
by both detection and replacement modules.
"""

from typing import Literal

from .schemas import PiiType


# Action type for de-identification
DeidentifyAction = Literal["replace", "redact"]


# Priority order for PII categories (higher = more important)
# Used when the same text appears in multiple categories to decide
# which category takes precedence
PII_PRIORITY: dict[PiiType, int] = {
    "NAME": 9,      # Highest priority - names are most sensitive
    "SCHOOL": 8,    # School names are highly identifying
    "LOCATION": 7,  # Locations can identify individuals
    "DATE": 6,      # Specific dates (birthdays, etc.)
    "AGE": 5,       # Age information
    "PHONE": 4,     # Contact information
    "EMAIL": 3,     # Contact information
    "URL": 2,       # Web addresses
    "MISC_ID": 1,   # Other identifiers (lowest priority)
}


# Human-readable redaction labels for each PII type
# Used when action="redact" to replace PII with placeholder text
REDACTION_LABELS: dict[PiiType, str] = {
    "NAME": "[name]",
    "LOCATION": "[location]",
    "SCHOOL": "[school]",
    "DATE": "[date]",
    "AGE": "[age]",
    "PHONE": "[phone number]",
    "EMAIL": "[email address]",
    "URL": "[URL]",
    "MISC_ID": "[ID]",
}


# Categories that use global (word-boundary) replacement
# These are replaced everywhere they appear in the text
GLOBAL_REPLACE_CATEGORIES: set[PiiType] = {
    "NAME",
    "LOCATION",
    "SCHOOL",
    "DATE",
    "EMAIL",
    "URL",
}


# Categories that use position-only replacement
# These are only replaced at the exact positions detected
# (to avoid replacing numbers that appear in math contexts)
POSITION_ONLY_CATEGORIES: set[PiiType] = {
    "AGE",
    "PHONE",
    "MISC_ID",
}


# Title prefixes that indicate the following word is a surname
# Names appearing after these should be treated as last names
TITLE_PREFIXES: set[str] = {
    "mr", "mr.", "mrs", "mrs.", "ms", "ms.", "miss", "dr", "dr.",
    "prof", "prof.", "professor", "tutor", "teacher", "coach",
    "grandma", "grandpa", "grandma's", "grandpa's",
    "aunt", "uncle", "auntie",
}


# Speaker title prefixes (subset of TITLE_PREFIXES used in metadata)
SPEAKER_TITLE_PREFIXES: set[str] = {
    "tutor", "mr", "mrs", "ms", "miss",
}


# Countries to skip replacement for LOCATION
# Replacing country names with fake city names is confusing
SKIP_COUNTRIES: set[str] = {
    "afghanistan", "albania", "algeria", "argentina", "australia", "austria",
    "bangladesh", "belgium", "brazil", "bulgaria", "cambodia", "cameroon",
    "canada", "chile", "china", "colombia", "costa rica", "croatia", "cuba",
    "czech republic", "denmark", "ecuador", "egypt", "el salvador", "england",
    "estonia", "ethiopia", "finland", "france", "germany", "ghana", "greece",
    "guatemala", "haiti", "honduras", "hungary", "iceland", "india", "indonesia",
    "iran", "iraq", "ireland", "israel", "italy", "jamaica", "japan", "jordan",
    "kenya", "korea", "kuwait", "latvia", "lebanon", "libya", "lithuania",
    "malaysia", "mexico", "morocco", "nepal", "netherlands", "new zealand",
    "nicaragua", "nigeria", "norway", "pakistan", "panama", "peru", "philippines",
    "poland", "portugal", "puerto rico", "qatar", "romania", "russia", "saudi arabia",
    "scotland", "senegal", "singapore", "south africa", "south korea", "spain",
    "sri lanka", "sudan", "sweden", "switzerland", "syria", "taiwan", "thailand",
    "turkey", "uganda", "ukraine", "united kingdom", "united states", "uruguay",
    "venezuela", "vietnam", "wales", "yemen", "zimbabwe",
    # Common abbreviations and alternate names
    "usa", "us", "uk", "uae",
}
