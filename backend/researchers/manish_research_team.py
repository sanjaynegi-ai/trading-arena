"""Specialist research agents used by Manish's custom trading workflow."""

from __future__ import annotations

import asyncio

from agents import Agent, Runner, Tool, function_tool

from backend.traders import get_model


SPECIALIST_MAX_TURNS = 4
COORDINATOR_MAX_TURNS = 1
MAX_SPECIALIST_BRIEF_CHARS = 2_000


def news_researcher_instructions() -> str:
    """Return instructions for the specialist that investigates current news."""

    return """You are Manish Kumar's News Researcher.
Research recent company, sector, and macroeconomic news relevant to a proposed
stock ticker or investment theme. Use the available search and fetch tools when
helpful.

Return a concise brief containing: ticker symbols considered, recent catalysts,
specific risks or negative news, sources or search terms used, and why each
finding may matter. Do not recommend or execute trades; provide evidence for
the Trader and Research Coordinator to evaluate.
"""


async def get_news_researcher(mcp_servers, model_name: str) -> Agent:
    """Build Manish's News Researcher with already-open research tools."""

    return Agent(
        name="Manish News Researcher",
        instructions=news_researcher_instructions(),
        model=get_model(model_name),
        mcp_servers=mcp_servers,
    )


async def get_news_researcher_tool(mcp_servers, model_name: str) -> Tool:
    """Expose the News Researcher as a tool for a future Coordinator agent."""

    researcher = await get_news_researcher(mcp_servers, model_name)
    return researcher.as_tool(
        tool_name="NewsResearcher",
        tool_description=(
            "Researches recent company, sector, and macro news. Returns "
            "catalysts, risks, ticker ideas, and sources for a proposed theme "
            "or ticker."
        ),
    )


def fundamentals_researcher_instructions() -> str:
    """Return instructions for the specialist that assesses company fundamentals."""

    return """You are Manish Kumar's Fundamentals Researcher.
Assess the underlying quality of a proposed company or ticker. Investigate its
business model, earnings, growth, cash generation, valuation context, competitive
position, and relevant financial risks using the available tools.

Return a concise brief containing: ticker symbols considered, business strengths,
financial evidence, valuation context when available, key weaknesses or risks,
sources or search terms used, and important unknowns. Do not recommend or
execute trades; provide balanced evidence for the Trader and Research
Coordinator to evaluate.
"""


async def get_fundamentals_researcher(mcp_servers, model_name: str) -> Agent:
    """Build Manish's Fundamentals Researcher with already-open research tools."""

    return Agent(
        name="Manish Fundamentals Researcher",
        instructions=fundamentals_researcher_instructions(),
        model=get_model(model_name),
        mcp_servers=mcp_servers,
    )


async def get_fundamentals_researcher_tool(mcp_servers, model_name: str) -> Tool:
    """Expose the Fundamentals Researcher for a future Coordinator agent."""

    researcher = await get_fundamentals_researcher(mcp_servers, model_name)
    return researcher.as_tool(
        tool_name="FundamentalsResearcher",
        tool_description=(
            "Assesses company quality, earnings, cash generation, valuation "
            "context, competitive position, and financial risks for a ticker."
        ),
    )


def technical_researcher_instructions() -> str:
    """Return instructions for the specialist that assesses market behaviour."""

    return """You are Manish Kumar's Technical Researcher.
Assess the market behaviour of a proposed ticker using available price and
market-context tools. Focus on trend direction, momentum, recent price action,
volatility, support or resistance context when justified by the data, and signs
that a trade may be poorly timed.

Return a concise brief containing: ticker symbols considered, observed trend or
momentum, relevant price context, possible entry or exit timing risks, important
limitations in the available data, and the tools or sources used. Do not
recommend or execute trades; provide measured market evidence for the Trader and
Research Coordinator to evaluate.
"""


async def get_technical_researcher(mcp_servers, model_name: str) -> Agent:
    """Build Manish's Technical Researcher with already-open market tools."""

    return Agent(
        name="Manish Technical Researcher",
        instructions=technical_researcher_instructions(),
        model=get_model(model_name),
        mcp_servers=mcp_servers,
    )


async def get_technical_researcher_tool(mcp_servers, model_name: str) -> Tool:
    """Expose the Technical Researcher for a future Coordinator agent."""

    researcher = await get_technical_researcher(mcp_servers, model_name)
    return researcher.as_tool(
        tool_name="TechnicalResearcher",
        tool_description=(
            "Assesses price trend, momentum, volatility, timing risk, and "
            "available market context for a ticker."
        ),
    )


def risk_researcher_instructions() -> str:
    """Return instructions for the specialist that challenges a trade idea."""

    return """You are Manish Kumar's Risk Researcher.
Act as a constructive skeptic for a proposed ticker, investment theme, or trade
idea. Look for negative news, weakening business signals, valuation concerns,
macroeconomic or sector risks, concentration concerns, and evidence that
contradicts the optimistic case.

Return a concise brief containing: risks found, counter-evidence, possible
downside triggers, conditions that would invalidate the thesis, important
unknowns, and the tools or sources used. If evidence is mixed or incomplete,
say so clearly. Do not recommend or execute trades; provide risk evidence for
the Trader and Research Coordinator to evaluate.
"""


async def get_risk_researcher(mcp_servers, model_name: str) -> Agent:
    """Build Manish's Risk Researcher with already-open research tools."""

    return Agent(
        name="Manish Risk Researcher",
        instructions=risk_researcher_instructions(),
        model=get_model(model_name),
        mcp_servers=mcp_servers,
    )


async def get_risk_researcher_tool(mcp_servers, model_name: str) -> Tool:
    """Expose the Risk Researcher for a future Coordinator agent."""

    researcher = await get_risk_researcher(mcp_servers, model_name)
    return researcher.as_tool(
        tool_name="RiskResearcher",
        tool_description=(
            "Challenges a proposed trade by finding counter-evidence, downside "
            "triggers, concentration concerns, and important unknowns."
        ),
    )


def research_coordinator_instructions() -> str:
    """Return instructions for Manish's multi-specialist research coordinator."""

    return """You are Manish Kumar's Research Coordinator.
You receive separate findings from News, Fundamentals, Technical, and Risk
specialists. Reconcile their findings without hiding disagreements or
uncertainty.

Return one concise research brief in this order:
1. Candidate ticker symbols considered
2. Recommendation: BUY, SELL, HOLD, or WATCH
3. Thesis and supporting evidence
4. Risks and counter-evidence
5. Technical or price context
6. Thesis invalidation condition
7. Confidence: low, medium, or high
8. Sources or search terms used

The recommendation is decision support only. Do not execute trades, call account
tools, or claim that an outcome is guaranteed. The Trader makes the final
decision after checking live market and account information.
"""


async def get_research_coordinator(model_name: str) -> Agent:
    """Build the lightweight Coordinator that synthesizes text findings."""

    return Agent(
        name="Manish Research Coordinator",
        instructions=research_coordinator_instructions(),
        model=get_model(model_name),
    )


def _compact_specialist_output(output: object) -> str:
    """Keep each specialist brief small enough for the Coordinator to synthesize."""

    text = str(output).strip()
    if len(text) <= MAX_SPECIALIST_BRIEF_CHARS:
        return text
    return f"{text[:MAX_SPECIALIST_BRIEF_CHARS]}\n[Brief truncated for synthesis]"


async def get_research_coordinator_tool(
    researcher_servers,
    technical_servers,
    model_name: str,
) -> Tool:
    """Expose a staged, multi-specialist research workflow to Manish's Trader."""

    news = await get_news_researcher(researcher_servers, model_name)
    fundamentals = await get_fundamentals_researcher(researcher_servers, model_name)
    technical = await get_technical_researcher(technical_servers, model_name)
    risk = await get_risk_researcher(researcher_servers, model_name)
    coordinator = await get_research_coordinator(model_name)

    @function_tool(
        name_override="ManishResearchTeam",
        description_override=(
            "Runs News, Fundamentals, Technical, and Risk research separately, "
            "then returns one evidence-based research brief for a ticker, theme, "
            "or market opportunity."
        ),
    )
    async def run_research_team(research_request: str) -> str:
        """Run the four specialists, then synthesize their compact findings."""

        specialist_runs = await asyncio.gather(
            Runner.run(news, research_request, max_turns=SPECIALIST_MAX_TURNS),
            Runner.run(
                fundamentals,
                research_request,
                max_turns=SPECIALIST_MAX_TURNS,
            ),
            Runner.run(
                technical,
                research_request,
                max_turns=SPECIALIST_MAX_TURNS,
            ),
            Runner.run(risk, research_request, max_turns=SPECIALIST_MAX_TURNS),
        )
        findings = "\n\n".join(
            [
                "News findings:\n" + _compact_specialist_output(specialist_runs[0].final_output),
                "Fundamentals findings:\n"
                + _compact_specialist_output(specialist_runs[1].final_output),
                "Technical findings:\n"
                + _compact_specialist_output(specialist_runs[2].final_output),
                "Risk findings:\n" + _compact_specialist_output(specialist_runs[3].final_output),
            ]
        )
        result = await Runner.run(
            coordinator,
            f"Research request:\n{research_request}\n\nSpecialist findings:\n{findings}",
            max_turns=COORDINATOR_MAX_TURNS,
        )
        return str(result.final_output)

    return run_research_team
