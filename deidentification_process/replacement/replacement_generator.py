"""
Replacement Data Generator Module.

Generates replacement data for all PII categories using the Faker library.
Integrates with the existing NameReplacer for name handling.

Supports two de-identification modes:
- REPLACE: Generate realistic fake data to replace PII
- REDACT: Replace PII with placeholder labels like "[email address]"
"""

import random
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

from faker import Faker

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared_resources import PiiType, ALL_PII_TYPES
from shared_resources.constants import (
    DeidentifyAction,
    REDACTION_LABELS,
    SKIP_COUNTRIES,
)
from .name_replacer import NameReplacer, detect_name_type
from .settings import SCHOOL_PREFIXES, SCHOOL_TYPES, ID_PREFIXES


class ReplacementGenerator:
    """Generates consistent replacement data for PII de-identification.

    Features:
    - Consistent mappings: Same input always produces same replacement
    - Locale support: Generate data matching regional formats
    - Integration with NameReplacer for intelligent name handling
    """

    def __init__(
        self,
        locale: str = "en_US",
        seed: Optional[int] = None,
        excluded_values: Optional[dict[PiiType, list[str]]] = None,
        force_last_names: Optional[list[str]] = None,
    ):
        """Initialize the replacement generator.

        Args:
            locale: Faker locale for regional data
            seed: Random seed for reproducible generation
            excluded_values: Dict of PII type -> values to avoid
            force_last_names: Names to always treat as surnames
        """
        self.locale = locale
        self.faker = Faker(locale)

        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)

        self._mappings: dict[PiiType, dict[str, str]] = defaultdict(dict)
        self._used: dict[PiiType, set[str]] = defaultdict(set)

        if excluded_values:
            for pii_type, values in excluded_values.items():
                self._used[pii_type].update(v.lower() for v in values)

        excluded_names = list(self._used.get("NAME", set()))
        self._name_replacer = NameReplacer(
            excluded_names=excluded_names,
            force_last_names=force_last_names,
            seed=seed,
        )

    def add_force_last_names(self, names: list[str]) -> None:
        """Add names that should always be treated as surnames."""
        self._name_replacer.add_force_last_names(names)

    def _normalize_key(self, value: str) -> str:
        """Normalize a value for consistent mapping lookup."""
        return value.strip().lower()

    def _get_or_create_mapping(
        self,
        pii_type: PiiType,
        original: str,
        generator_fn
    ) -> str:
        """Get existing mapping or create a new one.

        Ensures the replacement differs from the original by adding the
        original to the used set before generating.
        """
        key = self._normalize_key(original)

        if key in self._mappings[pii_type]:
            return self._mappings[pii_type][key]

        # Add original to used set to prevent generating the same value
        self._used[pii_type].add(key)

        max_attempts = 50
        for _ in range(max_attempts):
            replacement = generator_fn()
            # Ensure replacement differs from original and isn't already used
            if replacement.lower() not in self._used[pii_type]:
                break

        self._mappings[pii_type][key] = replacement
        self._used[pii_type].add(replacement.lower())
        return replacement

    def replace_name(self, name: str, is_first_name: Optional[bool] = None) -> str:
        """Replace a name using the NameReplacer.

        Args:
            name: The name to replace
            is_first_name: If True, treat as first name. If False, treat as
                          last name. If None, auto-detect.
        """
        if not name or not name.strip():
            return name

        if is_first_name is None:
            return self._name_replacer.replace_name_auto(name)
        elif is_first_name:
            return self._name_replacer.replace_first_name(name)
        else:
            return self._name_replacer.replace_last_name(name)

    def replace_location(self, location: str) -> str:
        """Replace a location with a fake one."""
        if not location or not location.strip():
            return location

        if location.strip().lower() in SKIP_COUNTRIES:
            return location

        def generate():
            parts = location.split(",")
            if len(parts) >= 2:
                return f"{self.faker.city()}, {self.faker.state_abbr()}"
            elif len(location.split()) > 3:
                return self.faker.street_address()
            else:
                return self.faker.city()

        return self._get_or_create_mapping("LOCATION", location, generate)

    def replace_school(self, school: str) -> str:
        """Replace a school name with a realistic fake school name."""
        if not school or not school.strip():
            return school

        def generate():
            school_lower = school.lower()
            detected_type = None

            for school_type in SCHOOL_TYPES:
                if school_type.lower() in school_lower:
                    detected_type = school_type
                    break

            prefix = random.choice(SCHOOL_PREFIXES)
            suffix = detected_type or random.choice(SCHOOL_TYPES)

            return f"{prefix} {suffix}"

        return self._get_or_create_mapping("SCHOOL", school, generate)

    def replace_date(self, date_str: str) -> str:
        """Replace a date while attempting to preserve the original format."""
        if not date_str or not date_str.strip():
            return date_str

        def generate():
            fake_date = self.faker.date_object()
            date_stripped = date_str.strip()

            # ISO format
            if re.match(r"^\d{4}-\d{2}-\d{2}$", date_stripped):
                return fake_date.strftime("%Y-%m-%d")
            # US format
            if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", date_stripped):
                return fake_date.strftime("%m/%d/%Y")
            # Long format
            if re.match(r"^[A-Za-z]+ \d{1,2},? \d{4}$", date_stripped):
                return fake_date.strftime("%B %d, %Y")
            # Just year
            if re.match(r"^\d{4}$", date_stripped):
                return str(self.faker.year())

            return fake_date.strftime("%m/%d/%Y")

        return self._get_or_create_mapping("DATE", date_str, generate)

    def replace_age(self, age: str) -> str:
        """Replace an age value with a plausible fake age."""
        if not age or not age.strip():
            return age

        def generate():
            age_stripped = age.strip()
            match = re.search(r"(\d+)", age_stripped)

            if match:
                original_age = int(match.group(1))
                new_age = max(1, min(120, original_age + random.randint(-5, 5)))
                suffix_match = re.search(r"\d+\s+(.+)$", age_stripped)
                if suffix_match:
                    return f"{new_age} {suffix_match.group(1)}"
                return str(new_age)

            return str(random.randint(5, 80))

        return self._get_or_create_mapping("AGE", age, generate)

    def replace_phone(self, phone: str) -> str:
        """Replace a phone number while preserving the general format."""
        if not phone or not phone.strip():
            return phone

        def generate():
            phone_stripped = phone.strip()

            if re.match(r"^\(\d{3}\)\s*\d{3}-\d{4}$", phone_stripped):
                return self.faker.numerify("(###) ###-####")
            elif re.match(r"^\d{3}-\d{3}-\d{4}$", phone_stripped):
                return self.faker.numerify("###-###-####")
            elif re.match(r"^\d{10}$", phone_stripped):
                return self.faker.numerify("##########")
            else:
                return self.faker.phone_number()

        return self._get_or_create_mapping("PHONE", phone, generate)

    def replace_email(self, email: str) -> str:
        """Replace an email address with a fake one."""
        if not email or not email.strip():
            return email

        def generate():
            email_stripped = email.strip().lower()

            if ".edu" in email_stripped:
                username = self.faker.user_name()
                return f"{username}@{self.faker.word()}.edu"
            if ".gov" in email_stripped:
                username = self.faker.user_name()
                return f"{username}@{self.faker.word()}.gov"

            return self.faker.email()

        return self._get_or_create_mapping("EMAIL", email, generate)

    def replace_url(self, url: str) -> str:
        """Replace a URL with a fake one."""
        if not url or not url.strip():
            return url

        def generate():
            url_stripped = url.strip()
            has_https = url_stripped.startswith("https://")
            has_http = url_stripped.startswith("http://")
            has_path = len(url_stripped.split("/")) > 3

            if has_https:
                base = f"https://{self.faker.domain_name()}"
            elif has_http:
                base = f"http://{self.faker.domain_name()}"
            else:
                base = self.faker.domain_name()

            if has_path:
                path = "/".join(self.faker.words(nb=2))
                return f"{base}/{path}"

            return base

        return self._get_or_create_mapping("URL", url, generate)

    def replace_misc_id(self, misc_id: str) -> str:
        """Replace a miscellaneous identifier with a fake one."""
        if not misc_id or not misc_id.strip():
            return misc_id

        def generate():
            id_stripped = misc_id.strip()

            prefix_match = re.match(r"^([A-Za-z]+)[-_]?(.+)$", id_stripped)
            if prefix_match:
                prefix = random.choice(ID_PREFIXES)
                numeric_part = prefix_match.group(2)
                if numeric_part.isdigit():
                    new_numeric = self.faker.numerify("#" * len(numeric_part))
                else:
                    new_numeric = self.faker.bothify("?" * len(numeric_part))
                separator = "-" if "-" in id_stripped else ("_" if "_" in id_stripped else "")
                return f"{prefix}{separator}{new_numeric}"

            if id_stripped.isdigit():
                return self.faker.numerify("#" * len(id_stripped))

            if re.match(r"^[a-f0-9-]{36}$", id_stripped.lower()):
                return self.faker.uuid4()

            return self.faker.bothify("?" * len(id_stripped)).upper()

        return self._get_or_create_mapping("MISC_ID", misc_id, generate)

    def replace(self, pii_type: PiiType, value: str) -> str:
        """Replace a PII value based on its type.

        Args:
            pii_type: The category of PII
            value: The original PII value

        Returns:
            A replacement value of the same type
        """
        replacers = {
            "NAME": lambda v: self.replace_name(v),
            "LOCATION": self.replace_location,
            "SCHOOL": self.replace_school,
            "DATE": self.replace_date,
            "AGE": self.replace_age,
            "PHONE": self.replace_phone,
            "EMAIL": self.replace_email,
            "URL": self.replace_url,
            "MISC_ID": self.replace_misc_id,
        }

        replacer = replacers.get(pii_type)
        if replacer:
            return replacer(value)

        return value

    def redact(self, pii_type: PiiType, value: str) -> str:
        """Redact a PII value by replacing it with a type-specific label.

        Args:
            pii_type: The category of PII
            value: The original PII value

        Returns:
            A redaction label like "[email address]" or "[name]"
        """
        if not value or not value.strip():
            return value

        label = REDACTION_LABELS.get(pii_type, f"[{pii_type}]")
        key = self._normalize_key(value)
        self._mappings[pii_type][key] = label

        return label

    def deidentify(
        self,
        pii_type: PiiType,
        value: str,
        action: DeidentifyAction = "replace"
    ) -> str:
        """De-identify a PII value using the specified action.

        Args:
            pii_type: The category of PII
            value: The original PII value
            action: "replace" for fake data, "redact" for placeholder labels

        Returns:
            De-identified value
        """
        if action == "redact":
            return self.redact(pii_type, value)
        else:
            return self.replace(pii_type, value)

    def get_mappings(self) -> dict[PiiType, dict[str, str]]:
        """Return all current mappings."""
        return dict(self._mappings)

    def get_name_replacer(self) -> NameReplacer:
        """Get the underlying NameReplacer for advanced name operations."""
        return self._name_replacer


def create_replacement_generator(
    locale: str = "en_US",
    seed: Optional[int] = None
) -> ReplacementGenerator:
    """Factory function to create a ReplacementGenerator.

    Args:
        locale: Faker locale
        seed: Random seed for reproducible generation

    Returns:
        Configured ReplacementGenerator instance
    """
    return ReplacementGenerator(locale=locale, seed=seed)


def create_actions_config(
    default_action: DeidentifyAction = "replace",
    redact: Optional[list[PiiType]] = None,
    replace: Optional[list[PiiType]] = None
) -> dict[PiiType, DeidentifyAction]:
    """Helper to create an actions configuration dictionary.

    Args:
        default_action: Default action for types not explicitly specified
        redact: List of PII types to redact
        replace: List of PII types to replace

    Returns:
        Dict mapping each PII type to its action

    Examples:
        # Redact everything
        actions = create_actions_config(default_action="redact")

        # Replace everything except emails and phones
        actions = create_actions_config(
            default_action="replace",
            redact=["EMAIL", "PHONE"]
        )
    """
    actions: dict[PiiType, DeidentifyAction] = {
        pii_type: default_action for pii_type in ALL_PII_TYPES
    }

    if redact:
        for pii_type in redact:
            actions[pii_type] = "redact"

    if replace:
        for pii_type in replace:
            actions[pii_type] = "replace"

    return actions
