from crossspec.hashing import hash_text


def test_hash_text_deterministic():
    result = hash_text("Hello  world")
    assert result["algo"] == "sha256"
    assert result["basis"] == "normalize_light"
    assert result["value"] == "64ec88ca00b268e5ba1a35678a1b5316d212f4f366b2477232534a8aeca37f3c"
