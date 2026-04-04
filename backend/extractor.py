"""Transcript entity extraction — fuzzy (n-gram) mode."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from rapidfuzz import fuzz, process

from config import FUZZY_MIN_WORD_LEN, FUZZY_NGRAM_THRESHOLD, FUZZY_PARTIAL_THRESHOLD

DATA_DIR = Path(__file__).parent


class Extractor:
    """
    Extracts NHL entities from a transcript using fuzzy matching.

    Returns canonical names and team abbreviations — no network calls, no stats.
    The server pipeline (server.py) calls StatsClient.lookup_player_id() and
    StatsClient.lookup_team_abbrev() on the returned values to resolve IDs/abbreviations
    before fetching live stats.

    Usage:
        extractor = Extractor()
        result = await extractor.extract_entities("McDavid scores against the Leafs")
        # {"players": ["Connor McDavid"], "teams": ["TOR"]}
    """

    def __init__(self) -> None:
        with open(DATA_DIR / "players.json", encoding="utf-8") as f:
            raw_players: dict[str, int] = json.load(f)
        with open(DATA_DIR / "teams.json", encoding="utf-8") as f:
            raw_teams: dict[str, str] = json.load(f)

        # Players — parallel lists indexed together
        self._player_names: list[str] = list(raw_players.keys())
        self._player_names_lower: list[str] = [n.lower() for n in self._player_names]

        # Teams — parallel lists indexed together
        self._team_names_lower: list[str] = [n.lower() for n in raw_teams.keys()]
        self._team_abbrevs: list[str] = list(raw_teams.values())

        self.fuzzy_ngram_threshold: int = FUZZY_NGRAM_THRESHOLD
        self.fuzzy_partial_threshold: int = FUZZY_PARTIAL_THRESHOLD

    def extract_entities(self, transcript: str) -> dict[str, list]:
        """
        Return {"players": [canonical_name, ...], "teams": [abbrev, ...]}
        without any network calls.
        """
        if not transcript.strip():
            return {"players": [], "teams": []}

        words = _tokenize(transcript)
        found_players: set[str] = set()
        found_teams: set[str] = set()

        # Pass 1 — n-gram window matching (n = 1, 2, 3)
        # Catches full and near-full name mentions, plus all single-word team aliases.
        for n in (1, 2, 3):
            for gram in _ngrams(words, n):
                p_hit = process.extractOne(
                    gram,
                    self._player_names_lower,
                    scorer=fuzz.ratio,
                    score_cutoff=self.fuzzy_ngram_threshold,
                )
                if p_hit:
                    found_players.add(self._player_names[p_hit[2]])

                t_hit = process.extractOne(
                    gram,
                    self._team_names_lower,
                    scorer=fuzz.ratio,
                    score_cutoff=self.fuzzy_ngram_threshold,
                )
                if t_hit:
                    found_teams.add(self._team_abbrevs[t_hit[2]])

        # Pass 2 — surname partial matching
        # Catches commentary-style last-name-only mentions, e.g. "McDavid" or "Pastrnak".
        # Teams are intentionally excluded here — their aliases are handled by pass 1.
        for word in words:
            if len(word) < FUZZY_MIN_WORD_LEN:
                continue
            p_hit = process.extractOne(
                word,
                self._player_names_lower,
                scorer=fuzz.partial_ratio,
                score_cutoff=self.fuzzy_partial_threshold,
            )
            if p_hit:
                found_players.add(self._player_names[p_hit[2]])

        return {
            "players": list(found_players),
            "teams": list(found_teams),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Lowercase, normalize separators, remove punctuation, split."""
    text = text.lower()
    text = re.sub(r"[-']", " ", text)       # hyphens & apostrophes → space
    text = re.sub(r"[^a-z0-9 ]", "", text)  # strip everything else
    return text.split()


def _ngrams(words: list[str], n: int) -> list[str]:
    return [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]


# ---------------------------------------------------------------------------
# Standalone verification: python extractor.py "<transcript>"
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _SAMPLES = [
        "McDavid scores against the Maple Leafs tonight",
        "Pastrnak with the assist, Draisaitl in the slot",
        "The Avalanche beat the Oilers four to two",
        "Rantanen sets up MacKinnon for the one-timer",
        "Nugent-Hopkins with a beauty goal",
    ]

    sentences = sys.argv[1:] if len(sys.argv) > 1 else _SAMPLES
    extractor = Extractor()

    for sentence in sentences:
        result = extractor.extract_entities(sentence)
        print(f"INPUT   : {sentence}")
        print(f"players : {result['players']}")
        print(f"teams   : {result['teams']}")
        print()
