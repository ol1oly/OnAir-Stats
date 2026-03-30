"""Centralized configuration constants for the NHL Radio Overlay backend.

Edit values here to tune the overlay's behaviour without touching
individual modules. Secrets (API keys) stay in .env — this file is
for defaults and tuning knobs only.

IMPORTANT: Any new tunable constant (timeout, threshold, URL, limit,
interval, model name, batch size) MUST be added here — never hardcoded
inline in a module.
"""

# ---------------------------------------------------------------------------
# NHL API
# ---------------------------------------------------------------------------

# Base URL for all NHL stats endpoints (player landing pages, standings)
NHL_API_BASE = "https://api-web.nhle.com/v1"

# Endpoint used to search for a player by name when they're not in players.json
NHL_SEARCH_URL = "https://search.d3.nhle.com/api/v1/search/player"

# URL template for team logo SVGs — {abbrev} is replaced with the 3-letter team code (e.g. "EDM")
NHL_LOGO_TEMPLATE = "https://assets.nhle.com/logos/nhl/svg/{abbrev}_light.svg"

# Max seconds to wait for any NHL API request before giving up
NHL_HTTP_TIMEOUT = 5

# How long (seconds) to keep player/team stats in memory before re-fetching from the API
NHL_CACHE_TTL = 45.0

# ---------------------------------------------------------------------------
# Entity extraction — fuzzy matching sensitivity
# ---------------------------------------------------------------------------

# Minimum similarity score (0–100) for matching a spoken phrase to a player/team name
# using full n-gram windows (e.g. "Connor McDavid"). Lower = more matches but more false positives.
FUZZY_NGRAM_THRESHOLD = 82

# Minimum similarity score (0–100) for matching a single surname mention
# (e.g. just "McDavid" in commentary). Higher than NGRAM because partial matches are riskier.
FUZZY_PARTIAL_THRESHOLD = 90

# Ignore words shorter than this in the surname-only pass (avoids matching "to", "the", etc.)
FUZZY_MIN_WORD_LEN = 4

# Minimum similarity score when falling back to the NHL search API for unknown players
SEARCH_MATCH_THRESHOLD = 85

# ---------------------------------------------------------------------------
# Deepgram transcriber
# ---------------------------------------------------------------------------

# Speech-to-text model to use (see Deepgram docs for alternatives)
DEEPGRAM_MODEL = "nova-2"

# Language for transcription — change to "fr" for French-language broadcasts
DEEPGRAM_LANGUAGE = "en"

# Max seconds between reconnection attempts when the Deepgram WebSocket drops
DEEPGRAM_RECONNECT_MAX_DELAY = 30.0
