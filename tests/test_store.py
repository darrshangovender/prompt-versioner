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