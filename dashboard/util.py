from __future__ import annotations


css = """
.arena-header {
    border-left: 6px solid #ecad0a;
    padding-left: 16px;
}

.leaderboard-table {
    border-collapse: collapse;
    width: 100%;
}

.leaderboard-table th,
.leaderboard-table td {
    border-bottom: 1px solid var(--border-color-primary);
    padding: 10px 12px;
    text-align: left;
}

.leaderboard-table th {
    color: var(--body-text-color-subdued);
    font-size: 0.82rem;
    text-transform: uppercase;
}

.leaderboard-table td.numeric,
.leaderboard-table th.numeric {
    text-align: right;
}

.leaderboard-table tr:last-child td {
    border-bottom: 0;
}

.positive-pnl {
    color: #1f9d62;
    font-weight: 700;
}

.negative-pnl {
    color: #d83b3b;
    font-weight: 700;
}

.positive-bg {
    background: color-mix(in srgb, #1f9d62 12%, transparent);
}

.negative-bg {
    background: color-mix(in srgb, #d83b3b 12%, transparent);
}

.trader-card {
    border: 1px solid var(--border-color-primary);
    border-radius: 8px;
    padding: 14px;
}

.metric-line {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    margin: 4px 0;
}

.metric-line span:first-child {
    color: var(--body-text-color-subdued);
}
"""
