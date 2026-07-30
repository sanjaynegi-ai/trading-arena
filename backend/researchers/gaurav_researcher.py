"""Custom researcher for Gaurav Jain's long-term, evidence-based trader."""

from __future__ import annotations

from agents import Agent, Tool

from backend.traders import get_model


def gaurav_researcher_instructions() -> str:
    """Return long-horizon research instructions for Gaurav's trader."""

    return """You are Gaurav Jain's market researcher.
Focus on durable businesses, strong fundamentals, sustainable competitive
advantages, and evidence-based conviction. Investigate recent earnings,
management commentary, balance-sheet strength, valuation context, and material
risks before forming a view.

Return a concise research brief with:
- candidate ticker symbols
- short thesis
- supporting evidence and sources
- key risks or counter-evidence
- what would change your view

Do not execute trades; provide evidence for the trader to evaluate.
"""


async def get_gaurav_researcher(mcp_servers, model_name: str) -> Agent:
    """Build Gaurav's custom researcher agent with the supplied MCP servers."""

    return Agent(
        name="GauravResearcher",
        instructions=gaurav_researcher_instructions(),
        model=get_model(model_name),
        mcp_servers=mcp_servers,
    )


async def get_gaurav_researcher_tool(mcp_servers, model_name: str) -> Tool:
    """Expose Gaurav's custom researcher as a tool for the trader agent."""

    researcher = await get_gaurav_researcher(mcp_servers, model_name)
    return researcher.as_tool(
        tool_name="GauravResearcher",
        tool_description=(
            "Researches durable businesses, fundamentals, catalysts, risks, and "
            "valuation context for Gaurav's long-term strategy."
        ),
    )
