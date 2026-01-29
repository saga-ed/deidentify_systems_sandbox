"""
Name Replacement Module.

Provides intelligent name replacement while preserving:
- First initial
- Gender (for first names)
- Country of origin (auto-detected)
- Similar/misspelled name grouping
"""

import random
from collections import defaultdict
from typing import Literal, Optional

from names_dataset import NameDataset

from .settings import COUNTRY_NAME_TO_ALPHA2


# Number of candidates to consider when selecting a random replacement
DEFAULT_CANDIDATE_POOL_SIZE = 5

# Initialize the dataset (singleton)
_nd: Optional[NameDataset] = None


def get_name_dataset() -> NameDataset:
    """Get or initialize the NameDataset singleton."""
    global _nd
    if _nd is None:
        _nd = NameDataset()
    return _nd


def extract_name(item) -> str:
    """Extract name string from auto_complete result item."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in ['name', 'Name', 'first_name', 'last_name']:
            if key in item:
                return item[key]
        if item:
            return list(item.keys())[0]
    return str(item)


def detect_country(name: str, use_first_name: bool = True) -> Optional[str]:
    """Detect the most likely country for a name.

    Args:
        name: The name to analyze
        use_first_name: Whether to search in first names (True) or last names (False)

    Returns:
        Alpha-2 country code or None if not found
    """
    nd = get_name_dataset()
    result = nd.search(name)
    key = "first_name" if use_first_name else "last_name"
    if not result or not result.get(key):
        return None
    country_info = result[key].get("country")
    if not country_info:
        return None
    country_name = max(country_info.items(), key=lambda x: x[1])[0]
    return COUNTRY_NAME_TO_ALPHA2.get(country_name)


def detect_gender(name: str) -> Optional[str]:
    """Detect the most likely gender for a first name.

    Args:
        name: The first name to analyze

    Returns:
        "Male" or "Female", or None if not found
    """
    nd = get_name_dataset()
    result = nd.search(name)
    if not result or not result.get("first_name"):
        return None
    gender_info = result["first_name"].get("gender")
    if not gender_info:
        return None
    male_prob = gender_info.get("Male", 0)
    female_prob = gender_info.get("Female", 0)
    return "Male" if male_prob >= female_prob else "Female"


NameType = Literal["first", "last", "unknown"]


def detect_name_type(name: str) -> NameType:
    """Detect whether a name is more likely a first name or last name.

    Uses the names_dataset to compare how commonly the name appears as a
    first name vs last name across countries.

    Args:
        name: The name to classify

    Returns:
        "first", "last", or "unknown"
    """
    nd = get_name_dataset()
    result = nd.search(name)

    if not result:
        return "unknown"

    first_info = result.get("first_name")
    last_info = result.get("last_name")

    if first_info and not last_info:
        return "first"
    if last_info and not first_info:
        return "last"
    if not first_info and not last_info:
        return "unknown"

    first_ranks = first_info.get("rank", {})
    last_ranks = last_info.get("rank", {})

    first_best = min((r for r in first_ranks.values() if r is not None), default=float("inf"))
    last_best = min((r for r in last_ranks.values() if r is not None), default=float("inf"))

    if first_best < last_best:
        return "first"
    if last_best < first_best:
        return "last"
    return "unknown"


def find_similar_names(names: list[str], use_first_name: bool = True) -> dict[str, list[str]]:
    """Group similar/misspelled names together using fuzzy matching.

    Args:
        names: List of names to group
        use_first_name: Whether to search in first names

    Returns:
        Dict mapping canonical name -> list of variants
    """
    if not names:
        return {}

    nd = get_name_dataset()
    names = list(set(n.strip() for n in names if n.strip()))

    groups = defaultdict(set)
    processed = set()

    for name in sorted(names, key=len, reverse=True):
        if name.lower() in processed:
            continue

        similar = nd.fuzzy_search(
            name=name,
            n=20,
            use_first_names=use_first_name
        )
        similar_names = [extract_name(s) for s in (similar or [])]

        group_key = name
        group_members = {name}

        for other in names:
            if other.lower() in processed:
                continue
            other_lower = other.lower()
            if any(s.lower() == other_lower for s in similar_names):
                group_members.add(other)
            elif len(other) >= 3 and len(name) >= 3:
                if other[:3].lower() == name[:3].lower():
                    if detect_gender(other) == detect_gender(name):
                        group_members.add(other)

        for member in group_members:
            processed.add(member.lower())

        if group_members:
            groups[group_key] = group_members

    return {k: list(v) for k, v in groups.items()}


class NameReplacer:
    """Replaces names while preserving characteristics.

    Features:
    - Preserves first initial
    - Preserves gender (for first names)
    - Auto-detects country of origin
    - Maps similar/misspelled names to the same replacement
    - Adds randomness by selecting from multiple plausible candidates
    """

    def __init__(
        self,
        excluded_names: Optional[list[str]] = None,
        force_last_names: Optional[list[str]] = None,
        candidate_pool_size: int = DEFAULT_CANDIDATE_POOL_SIZE,
        seed: Optional[int] = None,
    ):
        """Initialize the name replacer.

        Args:
            excluded_names: Names to avoid when generating replacements
            force_last_names: Names to always treat as surnames
            candidate_pool_size: Number of top candidates to randomly select from
            seed: Random seed for reproducible replacements
        """
        if seed is not None:
            random.seed(seed)

        self.excluded = set(n.lower() for n in (excluded_names or []))
        self._force_last_names = set(n.lower() for n in (force_last_names or []))
        self.first_name_mappings: dict[str, str] = {}
        self.last_name_mappings: dict[str, str] = {}
        self.similarity_groups: dict[str, str] = {}
        self._nd = get_name_dataset()
        self._candidate_pool_size = candidate_pool_size

    def add_force_last_names(self, names: list[str]) -> None:
        """Add names that should always be treated as surnames."""
        self._force_last_names.update(n.lower() for n in names)

    def add_excluded(self, names: list[str]):
        """Add names to the exclusion list."""
        self.excluded.update(n.lower() for n in names)

    def preprocess_similar_names(self, names: list[str], use_first_name: bool = True):
        """Group similar/misspelled names for consistent replacement."""
        groups = find_similar_names(names, use_first_name)
        for canonical, variants in groups.items():
            for variant in variants:
                self.similarity_groups[variant.lower()] = canonical

    def _get_canonical(self, name: str) -> str:
        """Get the canonical form of a name (for similarity grouping)."""
        return self.similarity_groups.get(name.lower(), name)

    def _get_replacement_candidate(
        self,
        name: str,
        use_first_name: bool,
        gender: Optional[str] = None,
        country: Optional[str] = None
    ) -> Optional[str]:
        """Get a replacement name from the dataset."""
        first_initial = name[0].upper()

        if not country:
            country = detect_country(name, use_first_name)

        kwargs = {
            "name": first_initial,
            "n": 50,
            "use_first_names": use_first_name,
        }
        if country:
            kwargs["country_alpha2"] = country
        if gender and use_first_name:
            kwargs["gender"] = gender

        raw_candidates = self._nd.auto_complete(**kwargs)

        if not raw_candidates and country:
            del kwargs["country_alpha2"]
            raw_candidates = self._nd.auto_complete(**kwargs)

        if not raw_candidates:
            return None

        candidates = [extract_name(c) for c in raw_candidates]
        candidates = [
            c for c in candidates
            if (c and
                c.upper().startswith(first_initial) and
                c.lower() != name.lower() and
                c.lower() not in self.excluded)
        ]

        if not candidates:
            return None

        pool_size = min(self._candidate_pool_size, len(candidates))
        return random.choice(candidates[:pool_size])

    def replace_first_name(self, name: str, country: Optional[str] = None) -> str:
        """Replace a first name preserving initial, gender, and country."""
        if not name:
            return name

        canonical = self._get_canonical(name)

        if canonical.lower() in self.first_name_mappings:
            return self.first_name_mappings[canonical.lower()]
        if name.lower() in self.first_name_mappings:
            return self.first_name_mappings[name.lower()]

        gender = detect_gender(name) or detect_gender(canonical)

        replacement = self._get_replacement_candidate(
            canonical, use_first_name=True, gender=gender, country=country
        )

        if not replacement:
            return name

        self.first_name_mappings[name.lower()] = replacement
        self.first_name_mappings[canonical.lower()] = replacement
        self.excluded.add(replacement.lower())

        return replacement

    def replace_last_name(self, name: str, country: Optional[str] = None) -> str:
        """Replace a last name preserving initial and country."""
        if not name:
            return name

        canonical = self._get_canonical(name)

        if canonical.lower() in self.last_name_mappings:
            return self.last_name_mappings[canonical.lower()]
        if name.lower() in self.last_name_mappings:
            return self.last_name_mappings[name.lower()]

        replacement = self._get_replacement_candidate(
            canonical, use_first_name=False, country=country
        )

        if not replacement:
            return name

        self.last_name_mappings[name.lower()] = replacement
        self.last_name_mappings[canonical.lower()] = replacement
        self.excluded.add(replacement.lower())

        return replacement

    def replace_names_batch(
        self,
        names: list[str],
        use_first_name: bool = True,
        group_similar: bool = True
    ) -> dict[str, str]:
        """Replace a batch of names.

        Args:
            names: List of names to replace
            use_first_name: True for first names, False for last names
            group_similar: If True, similar names get same replacement

        Returns:
            Dict mapping original names to replacements
        """
        if group_similar:
            self.preprocess_similar_names(names, use_first_name)

        result = {}
        replace_fn = self.replace_first_name if use_first_name else self.replace_last_name

        for name in names:
            result[name] = replace_fn(name)

        return result

    def replace_name_auto(self, name: str, country: Optional[str] = None) -> str:
        """Replace a name, automatically detecting if it's first or last.

        Args:
            name: The name to replace
            country: Optional country code to constrain replacements

        Returns:
            A replacement name of the same type
        """
        if not name:
            return name

        if name.lower() in self._force_last_names:
            return self.replace_last_name(name, country)

        name_type = detect_name_type(name)

        if name_type == "last":
            return self.replace_last_name(name, country)
        return self.replace_first_name(name, country)

    def get_mappings(self) -> dict:
        """Return all current mappings."""
        return {
            "first_names": dict(self.first_name_mappings),
            "last_names": dict(self.last_name_mappings),
            "similarity_groups": dict(self.similarity_groups)
        }
