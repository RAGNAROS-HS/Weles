# Research Guidelines

When calling `search_reddit`, pass the most specific subcategory that matches the user's query using the `subcategory` parameter — the server resolves it to the right subreddits. Available subcategories for the current mode are listed in your system context. If none fits, omit `subcategory` and the general list for this mode is used. If the user explicitly names a subreddit, pass it via `subreddits` instead.

When interpreting search results, each result carries a `credibility` field (`high`, `medium`, `low`, or `flagged`).

- Heavily discount `low` and `flagged` results. Treat them as weak signal only — do not base recommendations primarily on them.
- If the result set includes `"batch_flag": "coordinated_positivity"`, mention the possibility of astroturfing or coordinated promotion to the user.
- Prefer `high` credibility results (community sources, high-score Reddit posts with ownership history) when drawing conclusions.
