import pytest

from api import confirmations


@pytest.fixture(autouse=True)
def _isolated_confirmations(tmp_path, monkeypatch):
    """Every test gets its own empty confirmations file; the repo's data/real/confirmations.json is never
    touched and never seeds the test file (it holds the real STOP 2 review record)."""
    monkeypatch.setenv("CONFIRMATIONS_PATH", str(tmp_path / "confirmations.json"))
    monkeypatch.setattr(confirmations, "default_path", lambda: tmp_path / "no-seed-confirmations.json")
