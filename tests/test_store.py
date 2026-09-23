import pytest

from prompt_versioner import PromptStore


def test_set_creates_v1_and_v2(tmp_path):
    s = PromptStore(tmp_path / "p.db")
    v1 = s.set("ext", "v1 body")
    v2 = s.set("ext", "v2 body")
    assert v1.version == 1
    assert v2.version == 2
    history = s.history("ext")
    assert [v.version for v in history] == [1, 2]


def test_set_is_idempotent_for_same_body(tmp_path):
    s = PromptStore(tmp_path / "p.db")
    a = s.set("ext", "same body")
    b = s.set("ext", "same body")
    assert a.version == b.version == 1


def test_get_routes_to_current(tmp_path):
    s = PromptStore(tmp_path / "p.db")
    s.set("ext", "v1")
    s.set("ext", "v2")
    s.promote("ext", 2)
    assert s.get("ext").version == 2

def test_split_route_without_hash_key_is_an_error_not_a_silent_no_op(tmp_path):
    """hash_key defaulted to the prompt *name* — a constant — so a weighted route
    collapsed onto a single version. `{1: 0.9, 2: 0.1}` served v2 to 0% or 100%
    of traffic depending purely on how the name hashed, with no error either way."""
    s = PromptStore(tmp_path / "p.db")
    s.set("extractor", "v1 body")
    s.set("extractor", "v2 body")
    s.route("extractor", {1: 0.9, 2: 0.1})
    with pytest.raises(ValueError, match="hash_key"):
        s.get("extractor")


def test_split_route_with_per_request_keys_actually_splits(tmp_path):
    s = PromptStore(tmp_path / "p.db")
    s.set("extractor", "v1 body")
    s.set("extractor", "v2 body")
    s.route("extractor", {1: 0.9, 2: 0.1})
    versions = [s.get("extractor", hash_key=f"req-{i}").version for i in range(400)]
    share_v2 = versions.count(2) / len(versions)
    assert 0.05 < share_v2 < 0.18, f"expected ~10% on v2, got {share_v2:.1%}"
    # and routing stays sticky for a given key
    assert s.get("extractor", hash_key="req-7").version == s.get("extractor", hash_key="req-7").version


def test_single_version_route_still_works_without_a_hash_key(tmp_path):
    s = PromptStore(tmp_path / "p.db")
    s.set("extractor", "v1 body")
    s.set("extractor", "v2 body")
    s.promote("extractor", 2)
    assert s.get("extractor").version == 2
