# Personal AI Agent — Plan

## What This Is

A deeply personalized AI agent that advises on shopping, lifestyle, diet, and fitness. Its core differentiator: all advice is grounded in community consensus and lived owner experience, never manufacturer copy or influencer content. It builds a persistent profile of the user and applies it to every response.

---

## Tone & Voice

Neutral and robotic. No warmth, no affirmations, no filler.

- No preamble, no trailing summaries, no encouragement
- Responses are factual and structured
- Conclusions stated directly, not softened
- **Bad:** "That's a tough one! Here are some options you might like..."
- **Good:** "Community consensus on X is split. Long-term owners report Y. Common failure point: Z."

---

## 1. Personalization Layer

The foundation. Everything else is filtered through it.

### Profile dimensions
| Dimension | What's tracked |
|---|---|
| Body | Height, weight, build, fitness level, injury history |
| Dietary | Restrictions, preferences, current approach |
| Taste | Aesthetic style (minimal / technical / classic), brand rejections |
| Lifestyle | Climate, activity level, living situation |
| Budget psychology | "Buy once buy right" vs. "good enough for now"; what they optimize for: longevity, aesthetics, or performance |
| Goals | Current fitness goal, dietary goal, lifestyle focus |
| History | Everything recommended, bought, tried, rated, returned |

### How it learns
- **Onboarding intake**: structured session to build the initial profile
- **Post-recommendation follow-up**: "did you end up buying it?" (opt-in, not automatic)
- **Outcome check-ins**: "did that work out?" surfaced after time has passed
- **Correction memory**: pushback on a recommendation updates the model of why
- **Passive pattern detection**: if the user consistently ignores a type of recommendation, stop making it
- **Profile decay**: data older than a threshold is flagged as uncertain; agent asks to reconfirm

---

## 2. Research Methodology — The Anti-Marketing Principle

Core rule: **never cite manufacturer claims as evidence.** All grounding comes from independent community sources.

### Source hierarchy
1. **Reddit** — primary. Both targeted subreddit search and general Reddit search.
2. **Hobbyist / enthusiast forums** — secondary. Higher signal density for specific categories (Styleforum, CoffeeGeek, Bodybuilding.com forums, WatchUSeek, etc.)
3. **Subreddit wikis / FAQ stickies** — distilled community consensus; prioritized over individual posts
4. **Aggregated owner reviews** — mined for recurring patterns, not averages
5. **General web** — last resort; filtered to community content only

### Signals to seek
- "I've owned this for X years" posts
- "What do you actually own/use" threads (not wishlists)
- Recurring failure modes across unrelated users
- Price-to-longevity patterns ("replaced 3 cheap ones, wish I'd bought the expensive one")
- What people switched to and why

### Signals to discard
- Manufacturer spec sheets and marketing language
- Affiliate-linked "Top 10 best" listicles
- Reviews from accounts with 1-2 posts
- Brand-owned channels and websites
- Influencer / sponsored content

### Recency handling
- Threads older than ~3 years about active product categories are deprioritized
- Agent flags when the best available data is old and the landscape may have changed
- Discontinued product threads are explicitly marked

### Subreddit routing by domain

**Shopping / gear**
- r/BuyItForLife — longevity focus
- r/frugalmalefashion / r/femalefashionadvice — value-conscious
- r/malefashionadvice / r/streetwear — style
- r/onebag — travel and minimalism
- r/EDC — everyday carry
- Category-specific: r/headphones, r/Coffee, r/MechanicalKeyboards, r/bicycling, etc.

**Diet / food**
- r/nutrition, r/EatCheapAndHealthy, r/MealPrepSunday
- Approach-specific: r/keto, r/veganfitness, r/carnivore, r/loseit, r/gainit

**Fitness / workout**
- r/fitness (general), r/weightroom (intermediate+), r/bodyweightfitness
- r/running, r/trailrunning, r/flexibility
- r/Supplements — community experience only, not marketing

---

## 3. Domain Modules

### Shopping
- **Category research**: given a need + budget + profile, synthesize community consensus picks with reasons
- **Product lookup**: long-term owner opinions, common failure points, what people switched to and why
- **Comparative**: X vs Y framed as community experience, not spec sheet diff
- **Quality signals**: material/construction indicators, country of origin patterns, warranty reputation, repairability
- **Red flags**: known QC regressions, brand quality decline over time, price-to-quality outliers
- **Buy timing**: based on community-reported sale cycles, not retailer pressure
- All filtered by user's aesthetic preferences and budget psychology

### Lifestyle
- Home, organization, routines — what people with sustained use report vs. what's trendy
- Product ecosystem advice — community consensus on what pairs well with what the user already owns
- Maintenance and care advice — how to extend lifespan of things owned
- Anti-trend filter: separates durable community consensus from current hype cycles

### Diet
- Meal suggestions aligned to the user's restrictions, macros, and current dietary approach
- Community-validated strategies — what people actually sustain, not just what studies suggest
- Recipe sourcing from community (not influencer / cookbook) sources
- Supplement guidance: community experience threads only; evidence strength explicitly flagged
- Honest tradeoff reporting: "X approach works but users commonly report Y difficulty"
- Tracks what the user has tried and whether it matched their goals

### Workout
- Program recommendations based on level, goal, available time, and equipment
- Community-vetted programs prioritized (5/3/1, GZCLP, Starting Strength, C25K, etc.) — proven iteration history
- Tracks current program and goals; adjusts advice accordingly
- Troubleshooting via community threads before escalating to "see a professional"
- Tracks what the user has tried and why they stopped (injury, boredom, plateau)

---

## 4. Cross-Cutting Behaviors

### Confidence calibration
- Always states signal strength explicitly: strong consensus / divided / thin data
- Surfaces minority opinions when a loud minority exists
- Shows reasoning, not just conclusion

### Anti-bias guards
- Affiliate-heavy sources discounted
- Astroturfing heuristics: new accounts, coordinated phrasing, suspiciously uniform positivity
- Geographic / availability filter: recommendations not accessible to the user are excluded
- Recency filter applied consistently

### Proactive surfacing (scoped)
- Only proactively surfaces topics the user has previously engaged with
- Flags QC issues or recalls on things in the user's ownership history
- Seasonal adjustments: gear, diet, and training advice relative to time of year

---

## 5. Open Questions

| # | Question | Current leaning |
|---|---|---|
| 1 | How opinionated on divided topics? | Tiered: strong consensus → single pick; divided → present both sides with framing |
| 2 | Contradictory subreddit cultures (e.g. r/keto vs r/nutrition)? | Surface the disagreement explicitly; don't pick a side unless user's profile provides a clear preference |
| 3 | How aggressive are follow-up prompts? | Opt-in only; user sets cadence preference during onboarding |
| 4 | Unsolicited proactive advice? | Only for domains the user has already engaged with; never cold |
| 5 | Stale Reddit data? | Flag it; don't suppress — user decides how to weight it |
