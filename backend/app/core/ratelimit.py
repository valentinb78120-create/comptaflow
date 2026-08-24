"""
Rate limiting minimaliste en mémoire (fenêtre glissante).

Suffisant pour la V1 mono-instance ; passer à Redis (même clé, même logique)
quand l'API sera répliquée sur plusieurs machines.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

_hits: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def check_rate_limit(key: str, max_calls: int, window_seconds: int = 60) -> bool:
    """
    Enregistre un appel pour *key* et retourne True s'il est autorisé,
    False si la limite (*max_calls* par *window_seconds*) est dépassée.
    """
    now = time.monotonic()
    cutoff = now - window_seconds

    with _lock:
        q = _hits[key]
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= max_calls:
            return False
        q.append(now)
        return True


def reset(key: str | None = None) -> None:
    """Vide les compteurs (tests)."""
    with _lock:
        if key is None:
            _hits.clear()
        else:
            _hits.pop(key, None)
