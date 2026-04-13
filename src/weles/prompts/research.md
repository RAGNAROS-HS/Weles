# Research Guidelines

When calling `search_reddit`, pass the most specific subcategory that matches the user's query using the `subcategory` parameter — the server resolves it to the right subreddits. Available subcategories for the current mode are listed in your system context. If none fits, omit `subcategory` and the general list for this mode is used. If the user explicitly names a subreddit, pass it via `subreddits` instead.
