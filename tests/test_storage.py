from bike_or_bust.storage import LocalStorage


def test_put_then_exists_and_no_temp_left(tmp_path):
    s = LocalStorage(tmp_path)
    assert not s.exists("a/b.bin")
    s.put("a/b.bin", b"x")
    assert s.exists("a/b.bin")
    assert (tmp_path / "a/b.bin").read_bytes() == b"x"
    assert not list(tmp_path.rglob("*.tmp"))
