# AGENTS.md

## MarkItDown tutorial (`microsoft/markitdown`)

MarkItDown converts files (PDF, DOCX, PPTX, XLSX, HTML, images, audio, ZIP, EPUB, YouTube URLs, CSV/JSON/XML) to Markdown for LLM consumption. Official docs: <https://github.com/microsoft/markitdown>.

### Environment

- A dedicated venv lives at `venv-markitdown/` in this project (Python 3.12, markitdown 0.1.7 with `[all]` extras).
- Activate it: `source venv-markitdown/bin/activate` (or call the binary directly, no activation needed).
- **Gotchas**:
  - The venv was created by `uv` while a now-deleted `.venv` existed; its script shebangs were repaired with `sed` to point at the renamed `venv-markitdown` path. If anything breaks with `bad interpreter`, re-run that repair.
  - The venv has **no pip** (uv-created). Install/upgrade packages with `uv pip install --python venv-markitdown/bin/python 'markitdown[all]'` or `uv pip list --python venv-markitdown/bin/python`.

### CLI usage

```sh
# convert to stdout
venv-markitdown/bin/markitdown path-to-file.pdf

# convert to a file
venv-markitdown/bin/markitdown path-to-file.pdf -o document.md

# pipe content
cat path-to-file.pdf | venv-markitdown/bin/markitdown
```

### Python API

```python
from markitdown import MarkItDown

md = MarkItDown(enable_plugins=False)
result = md.convert("test.pdf")
print(result.text_content)
```

Optional extras can be installed individually: `markitdown[pdf, docx, pptx]`. For OCR on scanned PDFs or vision descriptions, pass `llm_client`/`llm_model` (e.g. OpenAI client). Azure Document Intelligence (`-d -e <endpoint>`) and Azure Content Understanding (`--use-cu --cu-endpoint ...`) provide cloud-based higher-fidelity conversion.

### Security note

`convert()` can reach local files, remote URIs, and byte streams — in untrusted contexts prefer the narrowest API (`convert_local()`, `convert_response()`, `convert_stream()`).
