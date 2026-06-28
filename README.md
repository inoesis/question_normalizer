# question_normalizer

Pure-Python normalization of scraped/third-party question dicts for LMS storage.

One public function. No web framework, no I/O, no global state.

## Install

```bash
pip install "question_normalizer @ git+ssh://git@github.com/inoesis/question_normalizer.git@main"
```

## Use

```python
from question_normalizer import normalize_questions

clean = normalize_questions(raw_questions)
```

Each input dict must have at minimum `question` (HTML string or `{text, ...}` dict),
`answers` (`list[str]`), and `correct_answers` (`list[int]`). Any extra keys
(`render_type`, `QB_id`, `quiz_question_tags`, …) round-trip unchanged.

## Pipeline

1. `html_repair` — merge duplicate `style` attrs, balance/close tags
2. `sanitizer`  — bleach + tinycss2 allowlist (tag / attr / CSS property)
3. `layout`    — light per-type guarantees (e.g. `alt`/`loading` on `<img>`)
4. `math_tex`  — KaTeX-source normalization (`\rm` → `\mathrm`, dedupe seps,
                 balanced-delimiter check)
5. answers     — stages 1+2+4 applied to each answer string
6. `validation` — `correct_answers` cleaned (range, dedupe, sort)

The function is fault-tolerant: a single malformed question never aborts the
batch — it returns a minimal-safe fallback record (`_normalize_error` set) so
output length and index order are stable.

## Test

```bash
pip install -e ".[dev]"
pytest
```

## Spec

See [`question_normalizer_spec.md`](../question_normalizer_spec.md) in the parent
project for the authoritative behaviour spec.
