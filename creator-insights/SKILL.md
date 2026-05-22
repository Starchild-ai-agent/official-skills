---
name: creator-insights
version: 1.0.1
description: |
  Twitter/X account analytics, viral patterns, VIP follower discovery, tweet drafting.

  Use when analyzing a creator's reach, finding hidden-gem followers, or drafting tweets in someone's style (e.g. score @vitalik, draft tweet on AI).

metadata:
  starchild:
    emoji: "📊"
    skillKey: creator-insights
    requires:
      env:
        - TWITTER_API_KEY
        - OPENROUTER_API_KEY 

user-invocable: true
disable-model-invocation: false

---

# Twitter Creator Insights

This skill provides Twitter/X content creators with actionable intelligence about their account performance, trending topics in their niche, and competitive analysis. Includes account analytics, viral content discovery, thread/follower intelligence, and AI-powered content generation.

## When to Use This Skill

Invoke this skill when:
- A creator requests analysis of their Twitter account or another account
- User asks about trending content or viral tweets in a specific niche
- User wants to understand what content performs well in their space
- User needs recommendations for improving their Twitter strategy
- User asks about competitor or similar account activity
- User wants to find influential accounts in a niche
- **User wants to identify VIP followers or "hidden gem" accounts** (NEW)
- **User asks which threads attracted high-value engagement** (NEW)
- **User needs help drafting tweets or analyzing viral patterns with AI** (NEW)
- **User wants to optimize an existing tweet before posting** (NEW)


## Core Workflow

The skill follows a **fetch → analyze → score → recommend** pipeline:

### 1. Account Analysis Phase

**Objective**: Deep-dive into a Twitter account's performance and content patterns.

**Process**:
1. Run `python scripts/twitter_analyzer.py --username [handle] --tweets 100`
2. The system fetches:
   - User profile (followers, bio, verification status)
   - Recent tweets (up to 100)
   - Engagement metrics (likes, RTs, replies, quotes, views)
3. Calculates:
   - Engagement rate (weighted by follower count)
   - Content patterns (hashtag usage, thread frequency, tweet types)
   - Posting schedule optimization
   - Viral content identification (outliers >2σ above mean)

**Key Metrics**:
- **Engagement Rate**: (likes + RTs + replies) / followers × 100
- **Like/RT Ratio**: Indicates passive vs. active engagement
- **Thread Performance**: Threads vs. standalone tweet comparison
- **Viral Multiplier**: How many times above average a tweet performed

**Output Structure**:
```
TWITTER ANALYSIS: @username
├── Profile metrics (followers, tweets, verification)
├── Engagement metrics (rates, averages, ratios)
├── Viral content (top 5 tweets with multiplier)
├── Thread analysis (performance comparison)
├── Hashtag performance (which hashtags drive engagement)
├── Posting schedule (best times based on data)
└── Recommendations (7 actionable insights)
```

### 2. Niche Detection Phase

**Objective**: Identify a creator's content niche and posting style.

**Process**:
1. Run `python scripts/profile_analyzer.py --profile @username`
2. Analyzes last 30 tweets for:
   - Keyword frequency across 14 predefined niches
   - Content themes (most common topics)
   - Tone analysis (professional, casual, educational, entertaining)
   - Posting cadence and consistency

**Niche Categories**:
- Tech, AI/ML, Crypto/Web3, Business, Marketing
- Gaming, Fitness, Beauty, Food, Travel
- Comedy, Education, Music, Art

**Scoring Method**:
```python
niche_score = Σ(keyword_matches) for niche in all_niches
primary_niche = max(niche_scores)
secondary_niches = scores > (primary_score × 0.5)
```

### 3. Trend Discovery Phase

**Objective**: Find viral content and trending topics in a specific niche.

**Process**:
1. Run `python scripts/trend_aggregator.py --niche "[topic]" --viral-examples --limit 10`
2. Search for tweets matching: `"{niche}" min_faves:1000 -is:retweet`
3. Rank by total engagement: `likes + (retweets × 2) + (replies × 1.5)`
4. Analyze viral factors:
   - Hashtag usage patterns
   - Tweet length optimization
   - Thread vs. single tweet
   - Question-based engagement
   - Quote tweet ratio (conversation starter indicator)

**Viral Factor Detection**:
```python
if len(hashtags) > 0: "used {n} hashtags"
if '?' in text: "engaged audience with question"
if len(text) > 200: "detailed/thorough content"
elif len(text) < 100: "concise and punchy"
if quotes > retweets/2: "sparked conversation"
```

### 4. Competitive Intelligence Phase

**Objective**: Identify top performers and rising accounts in a niche.

**Process**:
1. Run `python scripts/trend_aggregator.py --niche "[topic]" --find-accounts --limit 10`
2. Aggregate top 50 viral tweets in niche
3. Group by author and calculate:
   - Total engagement across all tweets
   - Average engagement per tweet
   - Follower count
4. Sort by engagement/follower ratio (efficiency metric)

**Account Scoring**:
```python
account_score = (total_engagement / follower_count) × tweet_frequency
# Identifies accounts that punch above their weight
```

### 5. Thread Intelligence Phase **NEW**

**Objective**: Identify high-performing threads and track engagement from influential accounts.

**Process**:
1. Run `python scripts/thread_intelligence.py --username [handle] --tweets 50 --threshold 10000`
2. Fetches user's timeline and identifies multi-tweet threads
3. For each thread:
   - Gets full thread context
   - Fetches all replies
   - Identifies high-value repliers (accounts with >10K followers by default)
   - Tracks engagement patterns
4. Ranks threads by number of high-value replies

**Influence Threshold**:
```python
high_value_account = follower_count >= threshold  # Default: 10,000
# Configurable via --threshold parameter
```

**Output Structure**:
```
THREAD INTELLIGENCE: @username
├── Thread Statistics (total, high-value reply count, engagement rate)
├── Top Threads (ranked by high-value replies)
│   ├── Thread text preview
│   ├── Tweet count in thread
│   ├── Total replies vs high-value replies
│   └── Reply engagement score
├── Top Thread Details (deep-dive on #1 thread)
│   ├── Full text preview
│   ├── High-value repliers list
│   └── Follower counts
└── Most Engaged High-Value Accounts (across all threads)
    ├── Reply count per account
    └── Number of threads engaged with
```

**Comparison Mode**:
```bash
python scripts/thread_intelligence.py --username [handle] --compare --tweets 50
```
Compares thread performance vs standalone tweets to determine optimal content format.

### 6. Follower Intelligence Phase **NEW**

**Objective**: Discover VIP followers using combined influence scoring and engagement tracking.

**Process**:
1. Run `python scripts/follower_intelligence.py --username [handle] --tweets 20 --max-followers 500`
2. Fetches user's followers (newest first, up to 500)
3. Tracks engagement across recent tweets:
   - Who retweeted (via `get_tweet_retweeters` endpoint)
   - Who replied (via `get_tweet_replies` endpoint)
4. Calculates influence score for each follower:
   ```python
   influence_score = (followers × 0.7) + (engagement_count × 1000 × 0.3)
   ```
5. Identifies special segments:
   - **VIP Followers**: Top 50 by influence score
   - **Hidden Gems**: <5K followers but ≥2 interactions
   - **Top Engagers**: Most interactions regardless of follower count

**Influence Score Formula**:
```python
# Balanced scoring: audience size (70%) + actual engagement (30%)
influence = (follower_count × 0.7) + (total_interactions × 1000 × 0.3)

# Example:
# Account A: 100K followers, 0 interactions = 70,000 influence
# Account B: 10K followers, 5 interactions = 8,500 influence
# Account C: 2K followers, 10 interactions = 4,400 influence (hidden gem!)
```

**Output Structure**:
```
VIP FOLLOWERS: @username
├── Engagement Statistics
│   ├── Total followers analyzed
│   ├── Engaged followers (who interacted)
│   └── Engagement rate %
├── Top VIP Followers (by influence score)
│   ├── Username, follower count, verified status
│   ├── Engagement breakdown (RTs, replies)
│   └── Influence score
├── Hidden Gems (high engagement, low followers)
│   └── Rising creators to nurture
└── Top Engagers (most interactions)
    └── Your biggest supporters
```

**Growth Analysis Mode**:
```bash
python scripts/follower_intelligence.py --username [handle] --growth --max-followers 200
```
Analyzes follower quality distribution (micro, small, medium, large, mega).

### 7. AI Content Generation Phase **NEW**

**Objective**: Use AI to analyze viral patterns, draft tweets, and optimize content using Claude 3.5 Sonnet.

**Three AI Actions**:

#### A. Viral Pattern Analysis
```bash
python scripts/content_generator.py --action analyze --username [top_creator] --tweets 50 --min-engagement 100
```

**Process**:
1. Fetches high-engagement tweets (>100 engagement by default)
2. Filters for viral content
3. Sends top 5 tweets to AI with prompt:
   - "Analyze content themes that perform best"
   - "Identify tweet structure patterns"
   - "Determine optimal posting times"
   - "Evaluate hashtag strategy"
   - "Understand engagement patterns"

**Output**: AI-generated multi-section analysis with actionable insights.

#### B. Tweet Drafting
```bash
python scripts/content_generator.py --action draft --topic "Your topic here" --username [style_reference] --variations 5
```

**Process**:
1. Optionally analyzes reference account's style (if --username provided)
2. Sends topic + style context to AI
3. AI generates 3-5 variations with:
   - Different angles/hooks per variation
   - Character count (ensures ≤280)
   - Strategy explanation
   - Predicted engagement level

**Output**: JSON array of tweet variations with metadata.

#### C. Tweet Optimization
```bash
python scripts/content_generator.py --action optimize --text "Your tweet draft" --goal engagement
```

**Goals**: `engagement`, `reach`, `replies`, `clarity`

**Process**:
1. Sends original tweet + optimization goal to AI
2. AI provides:
   - Optimized version
   - 2-3 alternative approaches
   - Explanation of improvements
   - Posting strategy tips

**Output**: Enhanced tweet with detailed optimization rationale.

### 8. Enhanced Viral Analysis **IMPROVED**

The viral factor detection has been significantly enhanced with multi-dimensional pattern analysis:

**Previous (Simple)**:
```python
if len(hashtags) > 0: "used hashtags"
if '?' in text: "question"
```

**New (Sophisticated)**:
```python
# 1. FORMAT DETECTION
- Thread detection (🧵, "thread", "1/")
- Question count (single vs multiple)
- List/numbered format (1. 2. 3.)
- Emotional hooks (amazing, shocking, breaking)
- Call-to-action (let me know, check out, reply with)

# 2. MEDIA DETECTION
- Visual content presence (images/videos)

# 3. LENGTH OPTIMIZATION
- Comprehensive (>240 chars)
- Concise (<80 chars)
- Optimal range (120-180 chars)

# 4. HASHTAG STRATEGY
- Strategic use (3+ hashtags)
- Focused single hashtag

# 5. ENGAGEMENT PATTERN ANALYSIS
- High reply ratio (>25% = discussion starter)
- High retweet ratio (>20% = shareable)
- Viral coefficient (quotes+RTs >30%)

# 6. TEMPORAL ANALYSIS
- Peak posting window (9-11 AM, 1-3 PM)
- Low-competition hours (9 PM - 6 AM)
- Weekend timing advantage

# 7. ADVANCED PATTERNS
- Data-driven credibility (study, research, analysis)
- Storytelling hooks (story, remember when)
- Controversy/debate (unpopular opinion, hot take)
```

**Example Enhanced Output**:
```
🔥 Why viral: Question encouraging replies; emotional hook driving curiosity;
comprehensive detail (long-form); highly shareable content
```

Returns top 4 most relevant factors for each viral tweet.

## Engagement Scoring Framework

Following **head-of-content** methodology, we use weighted engagement metrics:

```python
WEIGHTS = {
    'bookmarks': 4.0,  # Strongest intent signal
    'replies': 2.0,    # Direct conversation
    'retweets': 1.5,   # Amplification
    'quotes': 2.5,     # Conversation + amplification
    'likes': 1.0,      # Baseline engagement
    'views': 0.01      # Reach indicator
}

engagement_score = Σ(metric × weight)
```

**Outlier Detection**:
Content scoring above `mean + (2.0 × standard_deviation)` is flagged as viral.

## Output Formats

### Text Output (default)
Human-readable reports with:
- Section headers and dividers
- Bullet points for key insights
- Numerical rankings
- Actionable recommendations

### JSON Output
Machine-readable data for:
- Integration with other tools
- Historical tracking
- Custom dashboard creation
- Multi-account comparison

Example:
```bash
python scripts/twitter_analyzer.py --username handle --output json > analysis.json
```

## Configuration

**Config File** (`config.yaml` - optional):
```yaml
# AI content generation settings
openrouter:
  default_model: "anthropic/claude-3.5-sonnet"
  temperature: 0.7
  max_tokens: 2000

# Influence scoring for follower/thread intelligence
influence:
  follower_weight: 0.7           # 70% weight on follower count
  engagement_weight: 0.3         # 30% weight on engagement
  high_value_threshold: 10000    # 10K+ followers = high-value
  hidden_gem_threshold: 5000     # <5K followers = potential gem
  min_engagement_interactions: 2 # Minimum interactions to count

# Viral analysis thresholds
viral:
  min_engagement: 100            # Minimum total engagement
  min_likes: 500                 # For trending searches
  high_reply_ratio: 0.25         # >25% replies = discussion
  high_retweet_ratio: 0.20       # >20% RTs = shareable
  viral_coefficient: 0.30        # >30% quotes+RTs = viral

# Tweet generation defaults
generation:
  num_variations: 5              # Default tweet variations
  max_length: 280                # Twitter character limit
  style_sample_size: 10          # Tweets to analyze for style

settings:
  rate_limit: 100                # Requests per minute
  default_timeframe: "30d"       # Analytics window
  cache_duration: 15             # Minutes to cache trends
```

## Error Handling

**Rate Limiting**:
- Automatic backoff when hitting API limits
- 60-second cooldown before retry
- Progress maintained across retries

**Authentication Failures**:
- If authentication errors occur, check platform configuration

**Network Timeouts**:
- 10-second timeout per request
- Automatic retry with exponential backoff
- Graceful degradation (returns partial results)

**Invalid Usernames**:
```
Could not fetch info for @username
```
→ Verify account exists and is not suspended

## Advanced Usage

### Batch Analysis
Analyze multiple accounts:
```bash
for account in account1 account2 account3; do
    python scripts/twitter_analyzer.py --username $account --output json > ${account}_analysis.json
done
```

### Automated Monitoring
Daily trend tracking:
```bash
# Add to crontab
0 9 * * * cd /path/to/skill && python scripts/trend_aggregator.py --niche "AI" --viral-examples --limit 10 >> daily_trends.log
```

### Comparative Analysis
Compare two accounts:
```bash
python scripts/twitter_analyzer.py --username account1 --output json > a1.json
python scripts/twitter_analyzer.py --username account2 --output json > a2.json
# Then compare engagement_rate, viral_multiplier, etc.
```

## Related Scripts

**Core Analytics**:
- `scripts/twitter_analyzer.py` - Comprehensive account analysis
- `scripts/profile_analyzer.py` - Niche detection and content classification
- `scripts/trend_aggregator.py` - Viral content and account discovery (enhanced)
- `scripts/analytics_calculator.py` - Historical performance metrics

**Advanced Intelligence (NEW)**:
- `scripts/thread_intelligence.py` - Thread analysis and high-value engagement tracking
- `scripts/follower_intelligence.py` - VIP follower discovery with influence scoring
- `scripts/content_generator.py` - AI-powered viral analysis and tweet generation

**Infrastructure**:
- `scripts/api_client.py` - Core Twitter API wrapper (enhanced with 10+ endpoints)
- `scripts/ascii_formatter.py` - Beautiful terminal dashboard formatting
- `scripts/test_new_features.py` - Test suite for validation
- `scripts/setup_config.py` - Interactive configuration wizard

## Integration with Other Skills

This skill complements:
- **Content planning skills**: Use viral patterns to inform content strategy
- **Copywriting skills**: Analyze successful tweet structures
- **Marketing skills**: Understand audience engagement patterns

## Metrics Glossary

- **Engagement Rate**: % of followers who interact with content
- **Viral Multiplier**: How many standard deviations above average
- **Like/RT Ratio**: Passive (likes) vs. active (RTs) engagement
- **Thread Performance**: Avg engagement on threaded vs. single tweets
- **Consistency Score**: Regularity of posting (0-10 scale)
- **Quote Rate**: Replies with quotes (conversation quality indicator)

## Best Practices

1. **Run weekly analysis** on your account to track trends
2. **Compare to competitors** in your niche for benchmarking
3. **Act on viral patterns** - replicate what works
4. **Monitor recommended posting times** based on your data
5. **Track hashtag performance** and iterate
6. **Experiment with threads** if data shows they outperform
7. **Focus on engagement rate** over vanity metrics

## Troubleshooting

**"Rate limit exceeded"**
→ Wait 60 seconds and retry

**"Request timed out"**
→ Reduce `--tweets` parameter or try again (network issue)

**Empty results**
→ Try broader niche keywords or lower `min_faves` threshold

**Proxy connection issues**
→ Check that sc-proxy is running and configured correctly in Star Child


### What's New in v2.0:
- **Thread Intelligence**: Identify high-value engagement in threads (10K+ followers)
- **Follower Intelligence**: VIP follower discovery with influence score algorithm
- **AI Content Generation**: OpenRouter integration for viral analysis & tweet drafting
- **Enhanced Viral Analysis**: 7-category sophisticated pattern detection
- **API Expansion**: 10+ new TwitterAPI.io endpoints (followers, retweeters, replies, threads)
- **ASCII Dashboards**: Beautiful terminal visualizations with progress bars
- **Comprehensive Config**: Documented settings for all thresholds and parameters

### Module Summary:
1. `twitter_analyzer.py` - Account analytics (v1.0 feature)
2. `profile_analyzer.py` - Niche detection (v1.0 feature)
3. `trend_aggregator.py` - Viral discovery (enhanced in v2.0)
4. `thread_intelligence.py` - Thread analysis (NEW in v2.0)
5. `follower_intelligence.py` - VIP follower tracking (NEW in v2.0)
6. `content_generator.py` - AI-powered content (NEW in v2.0)


