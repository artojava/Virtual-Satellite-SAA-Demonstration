"""Virtual satellite demonstration and command-line entry point."""

import sys
from pathlib import Path

from streamlit.web import cli


def main() -> None:
    """Launch the packaged Streamlit application; forward server options."""

    app = Path(__file__).with_name("app.py")
    sys.argv = ["streamlit", "run", str(app), *sys.argv[1:]]
    cli.main()
