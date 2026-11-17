"""Model choices and saved-model migration; local fixtures, no provider calls."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from test_dashboard import SETTINGS, login

from agentic_web_demo.agents.openai_planner import ModelSettings
from agentic_web_demo.dashboard.accounts import Accounts
from agentic_web_demo.dashboard.app import ModelKey, create_app
from agentic_web_demo.dashboard.service import DashboardService
from agentic_web_demo.model_catalog import (
    DEFAULT_MODEL,
    MODEL_OPTIONS,
    model_catalog,
    supported_model,
)


PASSWORD = "model-catalog-fixture-password"


class MemoryStore:
    available = True
    label = "Fixture credential store"

    def __init__(self):
        self.values = {}
        self.writes = 0

    def save(self, user_id, settings):
        self.values[user_id] = settings
        self.writes += 1

    def load(self, user_id):
        return self.values[user_id]

    def forget(self, user_id):
        self.values.pop(user_id, None)


def test_catalog_default_and_documented_general_purpose_choices():
    assert DEFAULT_MODEL == "gpt-5.6-luna"
    assert {option["id"] for option in MODEL_OPTIONS} == {
        "gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol",
        "gpt-6-luna", "gpt-6-sol", "gpt-6-astra",
        "gpt-6.1-terra", "gpt-6.1-sol", "gpt-6.2-sol", "gpt-6.2-astra",
    }
    assert len({option["id"] for option in MODEL_OPTIONS}) == len(MODEL_OPTIONS)
    assert all(supported_model(option["id"]) for option in MODEL_OPTIONS)


def test_catalog_responses_cannot_mutate_future_choices():
    exposed = model_catalog()
    exposed["model_options"][0]["id"] = "gpt-5.4-mini"
    exposed["model_options"].clear()
    fresh = model_catalog()
    assert fresh["default_model"] == DEFAULT_MODEL
    assert fresh["model_options"][0]["id"] == DEFAULT_MODEL
    assert len(fresh["model_options"]) == 10


@pytest.mark.parametrize("model", [
    "gpt-5.4-mini", "gpt-5.6", "gpt-5.6-luna-2026-11-01", "gpt-7-future",
    "gpt-image-1", "whisper-1", "fixture-model", "", None, [],
])
def test_undocumented_older_and_specialized_models_are_not_catalog_choices(model):
    assert not supported_model(model)


def test_api_connection_defaults_to_luna_without_creating_a_provider_client():
    values = ModelKey(api_key="fixture-only", authorized=True)
    assert values.model == DEFAULT_MODEL


@pytest.mark.parametrize("option", MODEL_OPTIONS, ids=lambda item: item["id"])
def test_each_catalog_choice_can_be_configured(option):
    assert ModelKey(api_key="fixture-only", model=option["id"], authorized=True).model == option["id"]


@pytest.mark.parametrize("model", ["gpt-5.4-mini", "gpt-5.6", "gpt-7-future"])
def test_configuration_boundary_rejects_models_outside_the_dropdown(model):
    with pytest.raises(ValidationError, match="current model list"):
        ModelKey(api_key="fixture-only", model=model, authorized=True)


def test_model_settings_stays_generic_for_explicit_cli_and_transport_fixtures():
    assert ModelSettings("fixture-model", "fixture-only").model == "fixture-model"


@pytest.mark.parametrize("saved_model", [DEFAULT_MODEL, "gpt-5.4-mini", "gpt-5.6"])
def test_saved_model_restore_is_explicit_and_never_rewrites_the_key(tmp_path, saved_model):
    store = MemoryStore()
    accounts = Accounts(tmp_path, Path("config/rules.yaml"), "http://127.0.0.1:8000",
                        credential_store=store)
    try:
        user = accounts.register("alice", PASSWORD)
        sid = accounts.sign_in(user, "alice")
        # Simulate a connection saved before the catalogue policy was introduced.
        saved = ModelSettings(saved_model, "private-key-sentinel")
        accounts.save_credential(sid, saved, True)
        accounts.sign_out(sid)
        restored = accounts.get(accounts.sign_in(user, "alice"))
        if supported_model(saved_model):
            assert restored.model_settings is saved
            assert restored.credential_notice == ""
        else:
            assert restored.model_settings is None
            assert "outside the current model list" in restored.credential_notice
            assert "saved key has not been deleted" in restored.credential_notice
            assert "private-key-sentinel" not in restored.credential_notice
        assert accounts.profile(user)["credential_saved"] == 1
        assert store.values[user] is saved and store.writes == 1
        assert b"private-key-sentinel" not in accounts.database.read_bytes()
    finally:
        accounts.close()


def test_dashboard_catalog_and_rejected_model_leave_existing_connection_unchanged(tmp_path):
    template = DashboardService(tmp_path, Path("config/rules.yaml"), "http://127.0.0.1:8000")
    app = create_app(SETTINGS, template)
    with TestClient(app, base_url="http://localhost") as client:
        app.state.accounts.credentials = MemoryStore()
        app.state.accounts.register("demo", SETTINGS.password)
        headers = login(client)
        before = client.get("/api/config").json()
        assert before["default_model"] == DEFAULT_MODEL
        assert before["model_options"] == model_catalog()["model_options"]
        response = client.post("/api/model-key", headers=headers, json={
            "api_key": "private-key-sentinel", "authorized": True,
        })
        assert response.status_code == 200
        configured = client.get("/api/config").json()
        assert configured["model"] == DEFAULT_MODEL
        assert configured["model_configured"] is True
        rejected = client.post("/api/model-key", headers=headers, json={
            "api_key": "rejected-key-sentinel", "model": "gpt-5.4-mini", "authorized": True,
        })
        assert rejected.status_code == 422
        assert "current model" in rejected.json()["detail"]
        assert "rejected-key-sentinel" not in rejected.text
        after = client.get("/api/config").json()
        assert after["model"] == DEFAULT_MODEL
        assert after["model_options"] == configured["model_options"]
        assert "private-key-sentinel" not in str(after)
        session = next(iter(app.state.accounts.sessions.values()))
        prior_settings = session.model_settings
        changed = client.post("/api/model-key", headers=headers, json={
            "api_key": "new-key-sentinel", "model": "gpt-6.2-astra", "authorized": True,
        })
        assert changed.status_code == 200
        assert client.get("/api/config").json()["model"] == "gpt-6.2-astra"
        assert session.model_settings.model == "gpt-6.2-astra"
        assert prior_settings.model == DEFAULT_MODEL
        assert prior_settings.api_key == "private-key-sentinel"
        assert client.get("/api/jobs").json() == []
