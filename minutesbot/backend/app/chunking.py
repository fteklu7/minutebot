import re

SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text):
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    return [s for s in SENTENCE_END.split(text) if s]


def chunk_text(text, max_words=120, overlap=1):
    """Group sentences into ~max_words chunks for search.

    Each chunk repeats the last `overlap` sentences of the previous one so an
    answer that sits on a chunk boundary still shows up with some context.
    """
    sentences = split_sentences(text)
    chunks = []
    current = []
    count = 0

    for s in sentences:
        words = len(s.split())
        if current and count + words > max_words:
            chunks.append(" ".join(current))
            current = current[-overlap:] if overlap else []
            count = sum(len(x.split()) for x in current)
        current.append(s)
        count += words

    if current:
        last = " ".join(current)
        # don't add a chunk that's only the overlap we already stored
        if not chunks or not chunks[-1].endswith(last):
            chunks.append(last)

    return chunks
