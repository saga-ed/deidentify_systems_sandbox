"""
Detection module settings and configuration.

Contains configurable settings for the PII detector, including:
- spaCy model configuration
- False positive filters
- ASR-specific patterns
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DetectorSettings:
    """Configuration settings for the PII detector.

    Attributes:
        model_name: spaCy model to use for NER (default: en_core_web_lg)
        min_name_rank: Maximum rank threshold for name validation using names_dataset
        enable_asr_patterns: Whether to detect spoken patterns (e.g., "five five five")
        enable_contextual_names: Whether to use conversational patterns for name detection
    """

    model_name: str = "en_core_web_lg"
    min_name_rank: int = 5000
    enable_asr_patterns: bool = True
    enable_contextual_names: bool = True


# Number word patterns for ASR matching
DIGIT_WORD_LIST = [
    "zero", "one", "two", "three", "four", "five",
    "six", "seven", "eight", "nine", "oh"
]
TEEN_WORD_LIST = [
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen"
]
TENS_WORD_LIST = [
    "twenty", "thirty", "forty", "fifty",
    "sixty", "seventy", "eighty", "ninety"
]
ALL_NUMBER_WORDS = DIGIT_WORD_LIST + TEEN_WORD_LIST + TENS_WORD_LIST

# Regex patterns (for use in compiled patterns)
DIGIT_WORDS = r'(?:' + '|'.join(DIGIT_WORD_LIST) + r')'
TEEN_WORDS = r'(?:' + '|'.join(TEEN_WORD_LIST) + r')'
TENS_WORDS = r'(?:' + '|'.join(TENS_WORD_LIST) + r')'

# Student ages: 0-19 (includes all teenagers who might be students)
STUDENT_AGE_WORDS = rf'(?:{DIGIT_WORDS}|{TEEN_WORDS})'

# Relation words for 3rd person age patterns
RELATION_WORDS = (
    r'(?:brother|sister|sibling|cousin|friend|buddy|bestie|bff|'
    r'son|daughter|kid|child|nephew|niece|grandchild|'
    r'classmate|teammate|roommate)'
)

# Possessive pronouns for 3rd person patterns
POSSESSIVE = r'(?:my|your|his|her|their|our)'

# School indicator words (order matters - longer phrases first)
SCHOOL_INDICATORS = [
    # Compound phrases first
    "junior high school", "senior high school", "high school", "middle school",
    "elementary school", "charter school", "magnet school", "public school",
    "catholic school", "christian school", "day school", "grammar school",
    "junior high", "senior high",
    # Single words last
    "elementary", "middle", "high",
    "school", "academy", "prep", "preparatory", "collegiate",
    "university", "college", "institute", "polytechnic",
]
SCHOOL_INDICATORS_SET = set(SCHOOL_INDICATORS)
SCHOOL_INDICATORS_PATTERN = r'(?:' + '|'.join(
    s.replace(' ', r'\s+') for s in SCHOOL_INDICATORS
) + r')'

# Single-letter variables to exclude from MISC_ID (common in math tutoring)
MATH_VARIABLE_LETTERS = {
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
}

# False positive names - words that spaCy incorrectly classifies as names
# Organized by category for maintainability
FALSE_POSITIVE_NAMES = {
    # Interjections and exclamations
    "alrighty", "mmhmm", "mhmm", "hahaha", "ouch", "ugh", "huh",
    "aloha", "dammit", "dang", "yay", "woohoo",
    "ok", "okay", "yeah", "yes", "no", "nope", "um", "uh", "ah", "oh", "wow",
    "good", "great", "nice", "cool", "right", "alright", "all", "fine", "sure",
    "haha", "whoopee", "bro", "oops", "damn", "dumbass",

    # Pronouns and determiners
    "i", "me", "you", "we", "they", "it", "this", "that", "these", "those",
    "my", "your", "his", "her", "its", "our", "their", "mine", "yours",

    # Numbers
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "first", "second", "third", "fourth", "fifth", "eighty",

    # Days and months
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",

    # Common words mistaken for names
    "everybody", "anybody", "somebody", "brother", "sister", "ladies",
    "participant", "unknown", "grandma", "grandpa", "superhero",
    "welcome", "mathematics", "confidence", "expression", "young",
    "culinary", "plantain", "wolf", "flash",

    # Adjectives/adverbs mistaken for names
    "fantastic", "simple", "soft", "worried", "verbally", "shut",
    "literally", "beautiful", "pretty", "excellent", "deep",

    # Math/academic terms
    "coordinate", "distance", "division", "multiplication", "residual",
    "examples", "speed", "dishes", "times",
    "divided", "plus", "minus", "equals", "equal", "sum", "product",
    "indefinite", "infinite", "variable", "coefficient", "exponent",
    "slope", "circle", "graph", "equation", "inverse", "linear",
    "run", "opposite", "practice", "sketch", "swell",

    # Products/brands
    "minecraft", "kahoot", "lays", "chromebook", "chromebooks",
    "jeopardy", "elmo", "desmos",

    # Tech/organizations
    "gpa", "nsa", "university",

    # Spanish words (common in bilingual transcripts)
    "muchas", "gracias", "bueno", "buena", "hola", "adios", "si", "como", "esta",
    "verdad", "sopre", "tasa", "tienemos", "volvemos",

    # Other false positives
    "ergo", "etc", "connects", "lines", "usos",

    # Prepositions and conjunctions
    "so", "in", "on", "at", "to", "for", "with", "from", "by", "and", "or", "but",
    "if", "then", "when", "where", "why", "how", "what", "which", "who", "whom",

    # Titles
    "mr", "mrs", "ms", "miss", "dr",

    # Greetings and politeness
    "thank", "thanks", "please", "sorry", "hello", "hi", "hey", "bye", "goodbye",

    # Common verbs and words
    "let", "here", "there", "now", "well", "away", "back", "again", "just",
    "go", "come", "get", "put", "take", "make", "see", "look", "know", "think",
    "say", "said", "tell", "told", "ask", "asked", "want", "need", "try",
    "start", "stop", "wait", "hold", "keep", "leave", "move", "turn", "show",
    "write", "read", "work", "play", "help", "touch", "click", "type",

    # Educational/classroom context
    "answer", "question", "problem", "number", "page", "slide", "board",
    "correct", "wrong", "right", "left", "top", "bottom", "side",

    # Body parts
    "mouth", "hand", "hands", "head", "face", "eye", "eyes",

    # Time references
    "minute", "minutes", "hour", "hours", "second", "seconds",

    # Colors
    "pink", "blue", "red", "green", "yellow", "orange", "purple", "black", "white",
}

# False positive locations - words incorrectly classified as GPE/LOC/ORG
FALSE_POSITIVE_LOCATIONS = {
    # School subjects
    "math", "english", "science", "history", "art",
    # Math terms
    "pemdas", "algebra", "geometry", "calculus", "infinity",
    # Platform/app names
    "google", "saga", "mathlap", "matthlap", "mathlab",
    # Common words
    "friends", "friend", "team", "teams", "brownie", "brownies",
    "pink", "blue", "red", "green", "yellow", "orange", "purple",
    "scs", "nice",
    "workspace", "workspaces", "session", "sessions",
    "student", "students", "tutor", "tutors", "teacher", "teachers",
    "class", "classes", "school", "lesson", "lessons",
}

# False positive dates - words incorrectly classified as DATE
FALSE_POSITIVE_DATES = {
    # Relative time
    "day", "today", "yesterday", "tomorrow", "now", "later",
    "morning", "afternoon", "evening", "night", "daytime", "nighttime",
    # Duration units
    "week", "month", "year", "years", "time", "minute", "hour", "second",
    "months", "weeks", "days", "hours", "minutes", "seconds",
    # Day names
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    # Number words
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
    "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty", "sixty",
}

# Generic school phrases to filter
GENERIC_SCHOOL_PHRASES = {
    "a high school", "the high school", "the high", "a school",
    "my school", "your school", "our school", "their school", "the school",
    "high school", "middle school", "elementary school",
    "what's your high", "in school", "at school", "to school", "from school",
}
