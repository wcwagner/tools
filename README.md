# UV Tools

Python-based tools (often via LLM) that can be run with `uv run <URL>`. 

This is *not* a PyPi package, and the `pyproject.toml` exists solely for IDE's to have the
requisite packages available for type-checking etc. It also contains `ruff` linting/formatting
rules for consistency across standalone tool scripts.


## mistral-pdf-to-md

Inspired by Simon Willison's [post](https://simonwillison.net/2025/Mar/7/mistral-ocr/).  Converts
PDF's (local or remote) to a markdown document.

For example, we can convert the [Case for Open Symbology](https://assets.bbhub.io/professional/sites/10/imported/solutions/sites/8/2015/10/630748781_GD_Open_Symbology_WP_151020.pdf) PDF to an [equivalent markdown file](https://gist.github.com/wcwagner/a2506f3559de37952ad657d495565f25).
```bash
export MISTRAL_API_KEY=...
export BBG_SYMBOLOGY_URL=...
uv run mistral-pdf-to-md.py ${BBG_SYMBOLOGY_UR}L -o bbg-open-symbology.md
# 2025-03-09 17:17:53 [info     ] Starting PDF to markdown conversion
# 2025-03-09 17:17:53 [info     ] Processing URL                 url=https://assets.bbhub.io/professional/sites/10/imported/solutions/sites/8/2015/10/630748781_GD_Open_Symbology_WP_151020.pdf
# HTTP Request: POST https://api.mistral.ai/v1/ocr "HTTP/1.1 200 OK"
# 2025-03-09 17:17:54 [info     ] Generating markdown           
# 2025-03-09 17:17:54 [info     ] Markdown file created          output_path=bbg-open-symbology.md
```
