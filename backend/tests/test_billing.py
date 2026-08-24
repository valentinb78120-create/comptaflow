"""Tests unitaires de la logique d'accès trial / abonnement."""
import uuid
from datetime import datetime, timedelta, timezone

from app.models.cabinet import Cabinet
from app.services.billing import has_access, trial_active


def make_cabinet(**overrides) -> Cabinet:
    defaults = dict(
        id=uuid.uuid4(),
        name="Cabinet Test",
        email="test@cabinet.fr",
        subscription_active=False,
        trial_ends_at=None,
    )
    defaults.update(overrides)
    return Cabinet(**defaults)


class TestTrialActive:
    def test_trial_en_cours(self):
        c = make_cabinet(trial_ends_at=datetime.now(timezone.utc) + timedelta(days=7))
        assert trial_active(c) is True

    def test_trial_expire(self):
        c = make_cabinet(trial_ends_at=datetime.now(timezone.utc) - timedelta(days=1))
        assert trial_active(c) is False

    def test_pas_de_trial(self):
        assert trial_active(make_cabinet(trial_ends_at=None)) is False

    def test_trial_naive_datetime_traite_comme_utc(self):
        # La DB peut renvoyer un datetime sans tz — ne doit pas lever d'exception
        c = make_cabinet(trial_ends_at=datetime.utcnow() + timedelta(days=3))
        assert trial_active(c) is True


class TestHasAccess:
    def test_abonne_sans_trial(self):
        c = make_cabinet(subscription_active=True)
        assert has_access(c) is True

    def test_trial_sans_abonnement(self):
        c = make_cabinet(trial_ends_at=datetime.now(timezone.utc) + timedelta(days=1))
        assert has_access(c) is True

    def test_ni_trial_ni_abonnement(self):
        c = make_cabinet(trial_ends_at=datetime.now(timezone.utc) - timedelta(days=30))
        assert has_access(c) is False
