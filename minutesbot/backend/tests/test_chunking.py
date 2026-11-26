from app.chunking import chunk_text, split_sentences


def test_split_sentences():
    assert split_sentences("Hi there. How are you?  Good!") == ["Hi there.", "How are you?", "Good!"]


def test_empty_text():
    assert chunk_text("") == []
    assert chunk_text("   \n ") == []


def test_short_text_is_one_chunk():
    assert chunk_text("One sentence. Two sentences.") == ["One sentence. Two sentences."]


def test_long_text_splits_with_overlap():
    sentences = [f"This is sentence number {i} in the meeting." for i in range(40)]
    chunks = chunk_text(" ".join(sentences), max_words=30, overlap=1)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c.split()) <= 30 + 8  # one sentence of slack
    # last sentence of each chunk starts the next one
    for a, b in zip(chunks, chunks[1:]):
        assert b.startswith(split_sentences(a)[-1])
    assert "number 39" in chunks[-1]


def test_one_giant_sentence_still_kept():
    words = " ".join(["word"] * 300) + "."
    assert chunk_text(words, max_words=50) == [words]
