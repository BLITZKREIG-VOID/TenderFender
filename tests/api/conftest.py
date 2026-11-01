import pytest


@pytest.fixture(autouse=True)
def _isolated_confirmations(tmp_path, monkeypatch):
    """Every test gets its own confirmations file; the repo's data/real/confirmations.json is never touched."""
    monkeypatch.setenv("CONFIRMATIONS_PATH", str(tmp_path / "confirmations.json"))
