import io

import pytest
from botocore.exceptions import ClientError

from bike_or_bust.storage import LocalStorage, R2Storage, storage_from_env


def test_put_then_exists_and_no_temp_left(tmp_path):
    s = LocalStorage(tmp_path)
    assert not s.exists("a/b.bin")
    s.put("a/b.bin", b"x")
    assert s.exists("a/b.bin")
    assert (tmp_path / "a/b.bin").read_bytes() == b"x"
    assert not list(tmp_path.rglob("*.tmp"))


class FakeS3:
    def __init__(self, head_code=None):
        self.head_code, self.puts = head_code, []

    def head_object(self, Bucket, Key):
        if self.head_code:
            raise ClientError({"Error": {"Code": self.head_code}}, "HeadObject")

    def put_object(self, Bucket, Key, Body):
        self.puts.append((Bucket, Key, Body))

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(b"payload:" + Key.encode())}

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return self

    def paginate(self, Bucket, Prefix):
        keys = ["b/2", "a/1", "b/1"]
        yield {"Contents": [{"Key": k} for k in keys if k.startswith(Prefix)]}
        yield {}  # a page with no Contents must not break listing


def test_r2_exists_true_when_head_succeeds():
    assert R2Storage(FakeS3(), "b").exists("k")


def test_r2_exists_false_only_on_not_found():
    assert not R2Storage(FakeS3("404"), "b").exists("k")


def test_r2_auth_error_is_not_mistaken_for_missing():
    with pytest.raises(ClientError):
        R2Storage(FakeS3("403"), "b").exists("k")


def test_r2_put_sends_bucket_key_body():
    fake = FakeS3()
    R2Storage(fake, "bucket").put("k", b"data")
    assert fake.puts == [("bucket", "k", b"data")]


def test_default_backend_is_local(tmp_path):
    s = storage_from_env({"BRONZE_DIR": str(tmp_path)})
    assert isinstance(s, LocalStorage) and s.root == tmp_path


def test_r2_backend_with_missing_vars_fails_loudly_not_falls_back():
    with pytest.raises(ValueError, match="R2_BUCKET"):
        storage_from_env(
            {
                "STORAGE_BACKEND": "r2",
                "R2_ACCOUNT_ID": "a",
                "R2_ACCESS_KEY_ID": "k",
                "R2_SECRET_ACCESS_KEY": "s",
            }
        )


def test_r2_backend_builds_r2_storage():
    env = {
        "STORAGE_BACKEND": "r2",
        "R2_ACCOUNT_ID": "acc",
        "R2_ACCESS_KEY_ID": "k",
        "R2_SECRET_ACCESS_KEY": "s",
        "R2_BUCKET": "bucket",
    }
    s = storage_from_env(env)
    assert isinstance(s, R2Storage) and s.bucket == "bucket"


def test_unknown_backend_rejected():
    with pytest.raises(ValueError, match="unknown STORAGE_BACKEND"):
        storage_from_env({"STORAGE_BACKEND": "s4"})


def test_local_get_and_list_keys_sorted_by_prefix_ignoring_temp(tmp_path):
    s = LocalStorage(tmp_path)
    s.put("city=nyc/b.bin", b"2")
    s.put("city=nyc/a.bin", b"1")
    s.put("city=sf/c.bin", b"3")
    (tmp_path / "city=nyc" / "half.bin.tmp").write_bytes(b"x")
    assert s.list_keys("city=nyc/") == ["city=nyc/a.bin", "city=nyc/b.bin"]
    assert s.get("city=nyc/a.bin") == b"1"


def test_r2_get_reads_body():
    assert R2Storage(FakeS3(), "b").get("k") == b"payload:k"


def test_r2_list_keys_filters_prefix_sorts_and_handles_empty_page():
    assert R2Storage(FakeS3(), "b").list_keys("b/") == ["b/1", "b/2"]
