from __future__ import annotations

import argparse

from dashboard.ui import create_ui, make_theme
from dashboard.util import css


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the Trading Arena dashboard.")
    parser.add_argument("--server-name", default=None)
    parser.add_argument("--server-port", type=int, default=None)
    args = parser.parse_args()

    create_ui().launch(
        server_name=args.server_name,
        server_port=args.server_port,
        theme=make_theme(),
        css=css,
        footer_links=["gradio", "settings"],
    )
