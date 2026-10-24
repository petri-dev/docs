# Petri documentation

[MkDocs](https://www.mkdocs.org/) site for **https://docs.petri.run**.

## Local development

Use Python 3.13:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m mkdocs serve
```

Open http://127.0.0.1:8000. Add Markdown under `docs/` and navigation in `mkdocs.yml`.
Run `python -m mkdocs build --strict` before submitting changes.

To check sidebar scroll tracking in a browser:

```bash
python -m pip install playwright
python -m playwright install chromium
python tests/check_toc.py
python tests/check_code_blocks.py
```
