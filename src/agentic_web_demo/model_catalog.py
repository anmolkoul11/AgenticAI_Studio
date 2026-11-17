"""Dashboard model choices verified against OpenAI's model documentation.

This is an explicit, local catalogue, not a provider discovery request. Keep the
documented general-purpose models that support Responses, structured outputs
and image input together so changing a choice does not change workflow paths.
"""

DEFAULT_MODEL = "gpt-5.6-luna"
VERIFIED_ON = "2026-11-17"
MODEL_OPTIONS = (
    {"id": "gpt-5.6-luna", "label": "GPT-5.6 Luna", "family": "GPT-5.6"},
    {"id": "gpt-5.6-terra", "label": "GPT-5.6 Terra", "family": "GPT-5.6"},
    {"id": "gpt-5.6-sol", "label": "GPT-5.6 Sol", "family": "GPT-5.6"},
    {"id": "gpt-6-luna", "label": "GPT-6 Luna", "family": "GPT-6"},
    {"id": "gpt-6-sol", "label": "GPT-6 Sol", "family": "GPT-6"},
    {"id": "gpt-6-astra", "label": "GPT-6 Astra", "family": "GPT-6"},
    {"id": "gpt-6.1-terra", "label": "GPT-6.1 Terra", "family": "GPT-6.1"},
    {"id": "gpt-6.1-sol", "label": "GPT-6.1 Sol", "family": "GPT-6.1"},
    {"id": "gpt-6.2-sol", "label": "GPT-6.2 Sol", "family": "GPT-6.2"},
    {"id": "gpt-6.2-astra", "label": "GPT-6.2 Astra", "family": "GPT-6.2"},
)
SUPPORTED_MODELS = frozenset(option["id"] for option in MODEL_OPTIONS)


def supported_model(value):
    """Only exact documented IDs are choices; never infer future model names."""
    return isinstance(value, str) and value in SUPPORTED_MODELS


def model_catalog():
    """Return independent JSON-safe choices without exposing provider credentials."""
    return {
        "default_model": DEFAULT_MODEL,
        "model_options": [dict(option) for option in MODEL_OPTIONS],
    }
