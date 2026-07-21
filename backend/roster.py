from __future__ import annotations

from dataclasses import dataclass


DEFAULT_MODEL = "gpt-5.4-mini"

MANY_MODELS = [
    "gpt-5.5",
    "deepseek-v4-flash",
    "gemini-3.5-flash",
    "grok-4.3",
]


@dataclass(frozen=True)
class TraderProfile:
    name: str
    lastname: str
    strategy: str
    model_name: str = DEFAULT_MODEL


sanjay_strategy = (
    "Invest in durable, cash-generating companies with strong products, clear "
    "competitive advantages, and reasonable valuation. Prefer patient entries "
    "over chasing short-term spikes."
)

neil_strategy = (
    "Seek momentum opportunities in liquid technology and growth names. Confirm "
    "that price strength is supported by recent news, earnings, or sector "
    "tailwinds before buying."
)

manish_strategy = (
    "Make evidence-based, risk-aware decisions. Prefer understandable companies "
    "with clear business strength, confirm ideas with recent news and market data, "
    "and avoid concentrated or impulsive trades."
)

TRADER_PROFILES: list[TraderProfile] = [
    TraderProfile(name="Sanjay", lastname="Negi", strategy=sanjay_strategy),
    TraderProfile(name="Neil", lastname="Sharma", strategy=neil_strategy),
    TraderProfile(name="Manish", lastname="Kumar", strategy=manish_strategy),
]


def resolve_model_names(use_many_models: bool) -> list[str]:
    """Return model names for the roster."""

    if not use_many_models:
        return [profile.model_name for profile in TRADER_PROFILES]

    return [
        MANY_MODELS[index] if index < len(MANY_MODELS) else DEFAULT_MODEL
        for index, _profile in enumerate(TRADER_PROFILES)
    ]
