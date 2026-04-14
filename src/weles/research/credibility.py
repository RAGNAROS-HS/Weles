import re
from typing import Any, Literal, cast

from weles.tools.reddit import RedditPost
from weles.tools.web import WebResult

CredibilityLabel = Literal["high", "medium", "low", "flagged"]

_OWNERSHIP_RE = re.compile(
    r"\b(owned?|had|using|used)\b.{0,40}\b(\d+)\s*(year|month)s?\b", re.DOTALL
)
_SWITCHED_RE = re.compile(r"\bswitched?\s+(from|away\s+from)\b")
_AFFILIATE_RE = re.compile(r"[?&](ref|aff|tag)=|/(go|out|recommends)/")

_TIERS: list[CredibilityLabel] = ["low", "medium", "high"]


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


def _ngrams(text: str, n: int) -> set[tuple[str, ...]]:
    words = text.lower().split()
    if len(words) < n:
        return set()
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def score_results(
    results: list[RedditPost | WebResult],
) -> dict[str, Any]:
    """Score all results, appending `credibility` to each. Returns dict with `results`
    and optional top-level `batch_flag` when coordinated positivity is detected."""
    labels = [score_result(r) for r in results]
    scored = [{**r, "credibility": label} for r, label in zip(results, labels, strict=True)]

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
        ngram_sets = [_ngrams(t, 4) for t in low_flagged_texts]
        counts: dict[tuple[str, ...], int] = {}
        for ns in ngram_sets:
            for gram in ns:
                counts[gram] = counts.get(gram, 0) + 1
        if any(count >= 3 for count in counts.values()):
            batch_flag = "coordinated_positivity"

    out: dict[str, Any] = {"results": scored}
    if batch_flag:
        out["batch_flag"] = batch_flag
    return out
