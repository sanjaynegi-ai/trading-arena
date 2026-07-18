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

diwaker_strategy = (
    "Seek momentum opportunities in liquid technology and growth names. Confirm "
    "that price strength is supported by recent news, earnings, or sector "
    "tailwinds before buying."
)

sabya_strategy = (
    "Use a balanced quality-and-value approach. Favor companies with healthy "
    "balance sheets, consistent profitability, and market pessimism that appears "
    "temporary rather than structural."
)

anuradha_strategy = (
    "Prioritize risk-aware diversification across resilient sectors. Trim "
    "overextended positions, avoid concentration, and use live market context "
    "before adding exposure."
)


TRADER_PROFILES: list[TraderProfile] = [
    TraderProfile(name="Sanjay", lastname="Negi", strategy=sanjay_strategy),
    TraderProfile(name="Diwaker", lastname="Sharma", strategy=diwaker_strategy),
    TraderProfile(name="Sabya", lastname="Sachi", strategy=sabya_strategy),
    TraderProfile(name="Anuradha", lastname="Sharma", strategy=anuradha_strategy),
]


def resolve_model_names(use_many_models: bool) -> list[str]:
    """Return model names for the roster."""

    if not use_many_models:
        return [profile.model_name for profile in TRADER_PROFILES]

    return [
        MANY_MODELS[index] if index < len(MANY_MODELS) else DEFAULT_MODEL
        for index, _profile in enumerate(TRADER_PROFILES)
    ]
