from app.retrieval.embeddings import embed_text


def test_embed_text_returns_384_length_float_vector():
    vector = embed_text("The lab confirmed the reaction rate increased with temperature.")
    assert isinstance(vector, list)
    assert len(vector) == 384
    assert all(isinstance(value, float) for value in vector)


def test_embed_text_is_deterministic_for_identical_input():
    text = "Photosynthesis converts light energy into chemical energy."
    first = embed_text(text)
    second = embed_text(text)
    assert first == second
