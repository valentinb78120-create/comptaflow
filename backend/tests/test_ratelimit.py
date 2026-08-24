"""Tests du rate limiter en mémoire."""
from app.core.ratelimit import check_rate_limit, reset


class TestRateLimit:
    def setup_method(self):
        reset()

    def test_sous_la_limite(self):
        for _ in range(5):
            assert check_rate_limit("k1", max_calls=5, window_seconds=60) is True

    def test_au_dela_de_la_limite(self):
        for _ in range(3):
            check_rate_limit("k2", max_calls=3, window_seconds=60)
        assert check_rate_limit("k2", max_calls=3, window_seconds=60) is False

    def test_cles_independantes(self):
        for _ in range(3):
            check_rate_limit("a", max_calls=3, window_seconds=60)
        assert check_rate_limit("a", max_calls=3, window_seconds=60) is False
        assert check_rate_limit("b", max_calls=3, window_seconds=60) is True

    def test_reset_specifique(self):
        for _ in range(3):
            check_rate_limit("c", max_calls=3, window_seconds=60)
        reset("c")
        assert check_rate_limit("c", max_calls=3, window_seconds=60) is True
