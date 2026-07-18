from __future__ import annotations

from dashboard.ui import create_ui, make_theme
from dashboard.util import css


if __name__ == "__main__":
    create_ui().launch(
        theme=make_theme(),
        css=css,
        footer_links=["gradio", "settings"],
    )
