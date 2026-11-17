"""Model-picker behavior using the local mocked dashboard; no real model calls."""

from test_dashboard_api_setup import setup_ui

from agentic_web_demo.model_catalog import DEFAULT_MODEL, SUPPORTED_MODELS


def test_picker_defaults_to_luna_and_contains_only_current_catalogue(setup_ui):
    picker = setup_ui.locator("#model-id")
    assert picker.evaluate("element => element.tagName") == "SELECT"
    assert picker.input_value() == DEFAULT_MODEL == "gpt-5.6-luna"
    assert set(picker.locator("option").evaluate_all("items => items.map(item => item.value)")) == SUPPORTED_MODELS
    assert "gpt-5.4-mini" not in picker.locator("option").evaluate_all("items => items.map(item => item.value)")


def test_choosing_a_model_does_not_start_requests(setup_ui):
    setup_ui.locator("#api-setup-open").click()
    setup_ui.locator("#model-id").select_option("gpt-6.2-sol")
    assert setup_ui.evaluate("fixtureRequests") == []
    assert setup_ui.evaluate("modelConfigured") is False


def test_explicit_save_uses_the_selected_model_and_keeps_it_after_refresh(setup_ui):
    setup_ui.locator("#api-setup-open").click()
    setup_ui.locator("#model-id").select_option("gpt-6.2-sol")
    setup_ui.evaluate("""async () => {
      $('api-key').value='fixture-only-not-a-real-key';
      await $('key-form').onsubmit({preventDefault(){},submitter:$('save-key')});
    }""")
    assert setup_ui.evaluate("fixtureModel") == "gpt-6.2-sol"
    assert setup_ui.locator("#model-id").input_value() == "gpt-6.2-sol"
    assert setup_ui.locator("#api-key").input_value() == ""
    assert [request["path"] for request in setup_ui.evaluate("fixtureRequests")
            if request["method"] == "POST"] == ["/api/model-key"]


def test_a_legacy_unconfigured_connection_shows_the_new_default(setup_ui):
    setup_ui.evaluate("""() => updateModelPicker({
      model_configured:false,model:'gpt-5.4-mini',...fixtureCatalog
    })""")
    assert setup_ui.locator("#model-id").input_value() == DEFAULT_MODEL
    assert setup_ui.evaluate("fixtureRequests") == []
