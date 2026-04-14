import re
from collections.abc import Sequence
from typing import Any, Literal, cast

from weles.tools.reddit import RedditPost
from weles.tools.web import WebResult
from weles.utils.paths import resource_path

CredibilityLabel = Literal["high", "medium", "low", "flagged"]

_OWNERSHIP_RE = re.compile(
    r"\b(owned?|had|using|used)\b.{0,40}\b(\d+)\s*(year|month)s?\b", re.DOTALL
)
_SWITCHED_RE = re.compile(r"\bswitched?\s+(from|away\s+from)\b")
_AFFILIATE_RE = re.compile(r"[?&](ref|aff|tag)=|/(go|out|recommends)/")

_ASTROTURF_PHRASES = frozenset(
    [
        "exceeded my expectations",
        "highly recommend",
        "five stars",
        "couldn't be happier",
        "absolutely love it",
    ]
)

_TIERS: list[CredibilityLabel] = ["low", "medium", "high"]
_geo_block_cache: dict[str, set[str]] = {}


def _promote(label: CredibilityLabel) -> CredibilityLabel:
    if label == "flagged":
        return "flagged"
    idx = _TIERS.index(label)
    return _TIERS[min(idx + 1, len(_TIERS) - 1)]


def _score_reddit(result: RedditPost) -> CredibilityLabel:
    score = result["score"]
    if score >= 100:
        label: CredibilityLabel = "high"
    elif score >= 20:
        label = "medium"
    else:
        label = "low"

    body = result["selftext_preview"] or ""
    if _OWNERSHIP_RE.search(body):
        label = _promote(label)
    if _SWITCHED_RE.search(body):
        label = _promote(label)

    return label


def _score_web(result: WebResult) -> CredibilityLabel:
    if _AFFILIATE_RE.search(result["url"]):
        return "flagged"
    source_type = result["source_type"]
    if source_type == "community":
        return "high"
    if source_type == "commercial":
        return "low"
    return "medium"


def score_result(result: RedditPost | WebResult) -> CredibilityLabel:
    if "score" in result:
        return _score_reddit(cast(RedditPost, result))
    return _score_web(result)


def _load_geo_block(country_code: str) -> set[str]:
    """Load and cache the geo-block domain list for a country code.

    Returns an empty set if no file exists for the country.
    """
    key = country_code.upper()
    if key in _geo_block_cache:
        return _geo_block_cache[key]
    try:
        path = resource_path(f"config/geo_blocks/{key}.txt")
        domains: set[str] = set()
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                domains.add(line.lower())
        _geo_block_cache[key] = domains
        return domains
    except OSError:
        _geo_block_cache[key] = set()
        return set()


def _ngrams(text: str, n: int) -> set[tuple[str, ...]]:
    words = text.lower().split()
    if len(words) < n:
        return set()
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def _has_astroturf_phrase(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in _ASTROTURF_PHRASES)


def score_results(
    results: Sequence[RedditPost | WebResult],
    country_code: str | None = None,
) -> dict[str, Any]:
    """Score all results, appending `credibility` to each.

    Also tags:
    - `affiliate: True` on web results with affiliate URLs
    - `available: False` on web results whose domain is in the country's geo-block list
      (only when `country_code` is provided and a geo-block file exists for that country)

    Returns dict with `results` and optional top-level `batch_flag`
    when coordinated positivity is detected.
    """
    labels = [score_result(r) for r in results]
    geo_block: set[str] = _load_geo_block(country_code) if country_code else set()

    scored: list[dict[str, Any]] = []
    for result, label in zip(results, labels, strict=True):
        scored_result: dict[str, Any] = {**result, "credibility": label}
        is_web = "score" not in result
        if is_web:
            web = cast(WebResult, result)
            if _AFFILIATE_RE.search(web["url"]):
                scored_result["affiliate"] = True
            if geo_block and web["domain"].lower() in geo_block:
                scored_result["available"] = False
        scored.append(scored_result)

    low_flagged_texts: list[str] = []
    for result, label in zip(results, labels, strict=True):
        if label not in ("low", "flagged"):
            continue
        if "score" in result:
            text = cast(RedditPost, result)["selftext_preview"] or ""
        else:
            text = result["snippet"] or ""
        low_flagged_texts.append(text)

    batch_flag: str | None = None
    if len(low_flagged_texts) >= 3:
        # Check n-gram overlap
        ngram_sets = [_ngrams(t, 4) for t in low_flagged_texts]
        counts: dict[tuple[str, ...], int] = {}
        for ns in ngram_sets:
            for gram in ns:
                counts[gram] = counts.get(gram, 0) + 1
        if any(count >= 3 for count in counts.values()):
            batch_flag = "coordinated_positivity"

        # Check for shared astroturfing phrases across all low/flagged results
        if batch_flag is None and all(_has_astroturf_phrase(t) for t in low_flagged_texts):
            batch_flag = "coordinated_positivity"

    out: dict[str, Any] = {"results": scored}
    if batch_flag:
        out["batch_flag"] = batch_flag
    return out
