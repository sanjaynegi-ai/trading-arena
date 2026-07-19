from __future__ import annotations

from html import escape
from typing import Any

import gradio as gr

from backend.accounts import INITIAL_BALANCE, Account
from backend.database import read_log
from backend.trading_arena import lastnames, model_names, names


ACCOUNT_REFRESH_SECONDS = 120
LOG_REFRESH_SECONDS = 0.5


class Trader:
    def __init__(self, name: str, lastname: str, model_name: str) -> None:
        self.name = name
        self.lastname = lastname
        self.model_name = model_name
        self.account = Account.get(name)

    @property
    def full_name(self) -> str:
        return f"{self.name} {self.lastname}"

    def reload(self) -> Account:
        self.account = Account.get(self.name)
        return self.account


class LeaderboardView:
    def __init__(self, traders: list[Trader]) -> None:
        self.traders = traders

    def rows(self) -> list[dict[str, float | str]]:
        rows: list[dict[str, float | str]] = []
        for trader in self.traders:
            account = trader.reload()
            portfolio_value = account.calculate_portfolio_value()
            pnl = account.calculate_profit_loss(portfolio_value)
            rows.append(
                {
                    "name": trader.full_name,
                    "model_name": trader.model_name,
                    "portfolio_value": portfolio_value,
                    "pnl": pnl,
                    "pnl_percent": pnl / INITIAL_BALANCE,
                }
            )
        return sorted(rows, key=lambda row: float(row["portfolio_value"]), reverse=True)

    def render(self) -> str:
        body = []
        for rank, row in enumerate(self.rows(), start=1):
            pnl = float(row["pnl"])
            pnl_class = "positive-pnl" if pnl >= 0 else "negative-pnl"
            bg_class = "positive-bg" if pnl >= 0 else "negative-bg"
            body.append(
                "<tr class=\"{bg_class}\">"
                "<td>{rank}</td>"
                "<td>{name}</td>"
                "<td>{model_name}</td>"
                "<td class=\"numeric\">{portfolio_value}</td>"
                "<td class=\"numeric {pnl_class}\">{pnl}</td>"
                "<td class=\"numeric {pnl_class}\">{pnl_percent}</td>"
                "</tr>".format(
                    bg_class=bg_class,
                    rank=rank,
                    name=escape(str(row["name"])),
                    model_name=escape(str(row["model_name"])),
                    portfolio_value=_money(float(row["portfolio_value"])),
                    pnl=_signed_money(pnl),
                    pnl_percent=_signed_percent(float(row["pnl_percent"])),
                    pnl_class=pnl_class,
                )
            )

        return (
            "<table class=\"leaderboard-table\">"
            "<thead><tr>"
            "<th>Rank</th>"
            "<th>Trader</th>"
            "<th>Model</th>"
            "<th class=\"numeric\">Portfolio Value</th>"
            "<th class=\"numeric\">P&amp;L</th>"
            "<th class=\"numeric\">P&amp;L %</th>"
            "</tr></thead>"
            f"<tbody>{''.join(body)}</tbody>"
            "</table>"
        )

    def make_ui(self) -> None:
        with gr.Row():
            with gr.Column():
                gr.Markdown("## Leaderboard")
                leaderboard = gr.HTML(value=self.render(), padding=True)

        timer = gr.Timer(value=ACCOUNT_REFRESH_SECONDS)
        timer.tick(
            fn=self.render,
            outputs=leaderboard,
            queue=False,
        )


class TraderView:
    def __init__(self, trader: Trader) -> None:
        self.trader = trader

    def reload(self) -> tuple[str, list[list[Any]], list[list[Any]], str]:
        account = self.trader.reload()
        portfolio_value = account.calculate_portfolio_value()
        pnl = account.calculate_profit_loss(portfolio_value)
        summary = (
            "<div class=\"trader-card\">"
            f"<h3>{escape(self.trader.full_name)}</h3>"
            f"<p>{escape(self.trader.model_name)}</p>"
            f"<div class=\"metric-line\"><span>Cash</span><strong>{_money(account.balance)}</strong></div>"
            f"<div class=\"metric-line\"><span>Portfolio</span><strong>{_money(portfolio_value)}</strong></div>"
            f"<div class=\"metric-line\"><span>P&amp;L</span><strong class=\"{_pnl_class(pnl)}\">{_signed_money(pnl)}</strong></div>"
            "</div>"
        )
        return (
            summary,
            self._holdings_rows(account),
            self._transaction_rows(account),
            self.reload_logs(),
        )

    def reload_logs(self) -> str:
        logs = read_log(self.trader.name, last_n=10)
        if not logs:
            return "No activity yet."

        return "\n".join(
            f"{row['datetime']} [{row['type']}] {row['message']}"
            for row in logs
        )

    def make_ui(self) -> None:
        summary, holdings, transactions, logs = self.reload()

        with gr.Column(scale=1, min_width=260):
            summary_html = gr.HTML(value=summary, padding=True)
            holdings_df = gr.Dataframe(
                value=holdings,
                headers=["Symbol", "Shares"],
                datatype=["str", "number"],
                label="Holdings",
                interactive=False,
            )
            transactions_df = gr.Dataframe(
                value=transactions,
                headers=["Time", "Type", "Symbol", "Shares", "Price"],
                datatype=["str", "str", "str", "number", "number"],
                label="Transactions",
                interactive=False,
            )
            logs_box = gr.Textbox(
                value=logs,
                label="Recent Logs",
                lines=8,
                interactive=False,
            )

        account_timer = gr.Timer(value=ACCOUNT_REFRESH_SECONDS)
        account_timer.tick(
            fn=self.reload,
            outputs=[summary_html, holdings_df, transactions_df, logs_box],
            queue=False,
        )

        log_timer = gr.Timer(value=LOG_REFRESH_SECONDS)
        log_timer.tick(
            fn=self.reload_logs,
            outputs=logs_box,
            queue=False,
        )

    @staticmethod
    def _holdings_rows(account: Account) -> list[list[Any]]:
        return [
            [symbol, quantity]
            for symbol, quantity in sorted(account.get_holdings().items())
        ]

    @staticmethod
    def _transaction_rows(account: Account) -> list[list[Any]]:
        rows = []
        for transaction in account.list_transactions()[-8:]:
            rows.append(
                [
                    transaction["timestamp"],
                    transaction["type"],
                    transaction["symbol"],
                    transaction["quantity"],
                    round(float(transaction["price"]), 2),
                ]
            )
        return rows


def create_ui() -> gr.Blocks:
    traders = [
        Trader(name, lastname, model_name)
        for name, lastname, model_name in zip(names, lastnames, model_names)
    ]

    with gr.Blocks(
        title="Trading Arena",
        fill_width=True,
    ) as demo:
        gr.Markdown(
            "# Trading Arena\nAutonomous traders, one scoreboard.",
            elem_classes=["arena-header"],
        )
        LeaderboardView(traders).make_ui()
        with gr.Row():
            for trader in traders:
                TraderView(trader).make_ui()

    return demo


def make_theme() -> gr.Theme:
    return gr.themes.Default(
        primary_hue="blue",
        secondary_hue="purple",
        neutral_hue="gray",
    )


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _signed_money(value: float) -> str:
    return f"+${value:,.2f}" if value >= 0 else f"-${abs(value):,.2f}"


def _signed_percent(value: float) -> str:
    return f"{value:+.2%}"


def _pnl_class(value: float) -> str:
    return "positive-pnl" if value >= 0 else "negative-pnl"
