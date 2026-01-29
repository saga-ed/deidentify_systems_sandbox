"""
Replacement module settings and configuration.

Contains configurable settings for PII replacement, including:
- Replacement generation options
- Name replacement templates
- School name templates
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ReplacementSettings:
    """Configuration settings for the replacement generator.

    Attributes:
        locale: Faker locale for regional data generation (e.g., 'en_US', 'de_DE')
        seed: Random seed for reproducible generation
        candidate_pool_size: Number of name candidates to randomly select from
    """

    locale: str = "en_US"
    seed: Optional[int] = None
    candidate_pool_size: int = 5


# School name templates for realistic generation
SCHOOL_PREFIXES = [
    "Lincoln", "Washington", "Jefferson", "Roosevelt", "Kennedy",
    "Madison", "Franklin", "Adams", "Jackson", "Hamilton",
    "Riverside", "Lakewood", "Westfield", "Eastview", "Northside",
    "Southgate", "Hillcrest", "Valley", "Mountain View", "Oak Grove",
    "Maple", "Cedar", "Pine", "Willow", "Birch"
]

SCHOOL_TYPES = [
    "Elementary School", "Middle School", "High School",
    "Academy", "Preparatory School", "Charter School",
    "Magnet School", "School", "Learning Center"
]

# Common ID prefixes for MISC_ID generation
ID_PREFIXES = [
    "ID", "REF", "STU", "EMP", "ACC", "CUS", "ORD", "TXN"
]

# Country name to alpha-2 code mapping for names_dataset compatibility
COUNTRY_NAME_TO_ALPHA2 = {
    "United Arab Emirates": "AE", "Afghanistan": "AF", "Albania": "AL", "Angola": "AO",
    "Argentina": "AR", "Austria": "AT", "Azerbaijan": "AZ", "Bangladesh": "BD",
    "Belgium": "BE", "Burkina Faso": "BF", "Bulgaria": "BG", "Bahrain": "BH",
    "Burundi": "BI", "Brunei": "BN", "Bolivia": "BO", "Brazil": "BR", "Botswana": "BW",
    "Canada": "CA", "Switzerland": "CH", "Chile": "CL", "Cameroon": "CM", "China": "CN",
    "Colombia": "CO", "Costa Rica": "CR", "Cyprus": "CY", "Czech Republic": "CZ",
    "Czechia": "CZ", "Germany": "DE", "Djibouti": "DJ", "Denmark": "DK", "Algeria": "DZ",
    "Ecuador": "EC", "Estonia": "EE", "Egypt": "EG", "Spain": "ES", "Ethiopia": "ET",
    "Finland": "FI", "Fiji": "FJ", "France": "FR", "United Kingdom": "GB", "Georgia": "GE",
    "Ghana": "GH", "Greece": "GR", "Guatemala": "GT", "Hong Kong": "HK", "Honduras": "HN",
    "Croatia": "HR", "Haiti": "HT", "Hungary": "HU", "Indonesia": "ID", "Ireland": "IE",
    "Israel": "IL", "India": "IN", "Iraq": "IQ", "Iran": "IR", "Iceland": "IS",
    "Italy": "IT", "Jamaica": "JM", "Jordan": "JO", "Japan": "JP", "Cambodia": "KH",
    "South Korea": "KR", "Korea": "KR", "Kuwait": "KW", "Kazakhstan": "KZ", "Lebanon": "LB",
    "Lithuania": "LT", "Luxembourg": "LU", "Libya": "LY", "Morocco": "MA", "Moldova": "MD",
    "Macau": "MO", "Malta": "MT", "Mauritius": "MU", "Maldives": "MV", "Mexico": "MX",
    "Malaysia": "MY", "Namibia": "NA", "Nigeria": "NG", "Netherlands": "NL", "Norway": "NO",
    "Oman": "OM", "Panama": "PA", "Peru": "PE", "Philippines": "PH", "Poland": "PL",
    "Puerto Rico": "PR", "Palestine": "PS", "Portugal": "PT", "Qatar": "QA", "Serbia": "RS",
    "Russia": "RU", "Saudi Arabia": "SA", "Sudan": "SD", "Sweden": "SE", "Singapore": "SG",
    "Slovenia": "SI", "El Salvador": "SV", "Syria": "SY", "Turkmenistan": "TM",
    "Tunisia": "TN", "Turkey": "TR", "Taiwan": "TW", "United States": "US", "Uruguay": "UY",
    "Yemen": "YE", "South Africa": "ZA"
}
