"""
Text preprocessing for the NLP stage of the AI workflow: strip noise,
tokenize, lemmatize, and remove stopwords, producing a normalized string
suitable for classification and embedding (not for display to a human —
`raw_text` remains the source of truth for anything user-facing).

**Primary path: spaCy** (`en_core_web_sm`). One pass gives us tokenization,
lemmatization, stopword flags, and (in ner.py) named entities together,
which is both simpler and more accurate than stitching NLTK pieces
together.

**Fallback path: NLTK.** If the spaCy English model hasn't been downloaded
in a given deployment (see backend/Dockerfile), we still clean text using
NLTK's tokenizer/stopwords/WordNet lemmatizer rather than failing outright.
NLTK has no comparable NER component, though, so location extraction
degrades to "no entity found" in that case — see ner.py.
"""

import re
from functools import lru_cache
from typing import Optional

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_WHITESPACE_RE = re.compile(r"\s+")


@lru_cache
def get_spacy_model():
    """Loads the spaCy pipeline once per process. Returns None (rather
    than raising) if the model isn't installed, so callers can fall back
    to NLTK instead of crashing the whole request."""
    import spacy

    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        return None


def _clean_with_spacy(nlp, text: str) -> str:
    doc = nlp(text)
    return " ".join(
        token.lemma_.lower()
        for token in doc
        if not token.is_stop and not token.is_punct and not token.is_space
    )


def _clean_with_nltk(text: str) -> str:
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer
    from nltk.tokenize import word_tokenize

    try:
        stop_words = set(stopwords.words("english"))
    except LookupError:
        nltk.download("stopwords", quiet=True)
        stop_words = set(stopwords.words("english"))

    try:
        tokens = word_tokenize(text)
    except LookupError:
        nltk.download("punkt", quiet=True)
        tokens = word_tokenize(text)

    lemmatizer = WordNetLemmatizer()
    return " ".join(
        lemmatizer.lemmatize(tok.lower())
        for tok in tokens
        if tok.isalpha() and tok.lower() not in stop_words
    )


def clean_text(raw_text: Optional[str]) -> str:
    """Lowercase, strip URLs/extra whitespace, then lemmatize and drop
    stopwords/punctuation. Empty/None input returns an empty string."""
    if not raw_text:
        return ""

    text = _URL_RE.sub(" ", raw_text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    if not text:
        return ""

    nlp = get_spacy_model()
    if nlp is not None:
        return _clean_with_spacy(nlp, text)
    return _clean_with_nltk(text)
