# Research Guidelines

When calling `search_reddit`, select the most specific subcategory that matches the user's query. For example, if the user asks about running shoes, prefer the `running` subcategory over `general`. If the user explicitly names a subreddit in their message, pass it directly to `search_reddit` instead of using the routing defaults.
