## UV Tools

Python-based tools (often via LLM) that can be run with `uv run <URL>`. 

This is *not* a PyPi package, and the `pyproject.toml` exists solely for IDE's to have the
requisite packages available for type-checking etc. It also contains `ruff` linting/formatting
rules for consistency across standalone tool scripts.