from prompt_versioner.routing import pick_version


def test_single_weight_always_picks_that():
    for key in ["a", "b", "c", "longer prompt body"]:
        assert pick_version({1: 1.0}, key) == 1


def test_50_50_split_is_roughly_balanced():
    counts = {1: 0, 2: 0}
    for i in range(10_000):
        counts[pick_version({1: 0.5, 2: 0.5}, str(i))] += 1
    # Should be within 1% of even.
    assert 4_800 < counts[1] < 5_200


def test_stable_for_same_key():
    key = "the same prompt"
    for _ in range(100):
        assert pick_version({1: 0.7, 2: 0.3}, key) == pick_version({1: 0.7, 2: 0.3}, key)