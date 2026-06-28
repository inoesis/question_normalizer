"""question_normalizer: pure-Python normalization of scraped/third-party question dicts.

The only supported public symbol is :func:`normalize_questions`.
"""

from .api import normalize_questions

__all__ = ["normalize_questions"]
__version__ = "0.1.0"
