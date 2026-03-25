"""
Fuzzy extraction test suite for extractor.py

Run from the backend/ directory:
    python tests/test_extractor.py

Each test case declares which players/teams MUST or MUST NOT appear in the result.
Sections:
  §1  Exact full names
  §2  Aliases  (Leafs → TOR, Avs → COL, etc.)
  §3  Surname-only mentions
  §4  Hardcoded ASR typos  (realistic Deepgram mis-transcriptions)
  §5  Programmatically generated char-level mutations
  §6  Multi-entity sentences
  §7  Edge cases / false-positive guard
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from extractor import Extractor


# ---------------------------------------------------------------------------
# Test-case schema
# ---------------------------------------------------------------------------

@dataclass
class TC:
    name:        str
    transcript:  str
    players_in:  set[str] = field(default_factory=set)  # must appear in result
    teams_in:    set[str] = field(default_factory=set)   # must appear in result
    players_out: set[str] = field(default_factory=set)  # must NOT appear
    teams_out:   set[str] = field(default_factory=set)   # must NOT appear


# ---------------------------------------------------------------------------
# Player name constants  (canonical names from players.json)
# ---------------------------------------------------------------------------

MC_DAVID    = "Connor McDavid"
DRAISAITL   = "Leon Draisaitl"
MACKINNON   = "Nathan MacKinnon"
MATTHEWS    = "Auston Matthews"
PASTRNAK    = "David Pastrnak"
KUCHEROV    = "Nikita Kucherov"
CROSBY      = "Sidney Crosby"
OVECHKIN    = "Alex Ovechkin"
MAKAR       = "Cale Makar"
MARNER      = "Mitch Marner"
M_TKACHUK   = "Matthew Tkachuk"
B_TKACHUK   = "Brady Tkachuk"
POINT       = "Brayden Point"
RANTANEN    = "Mikko Rantanen"
VASILEVSKIY = "Andrei Vasilevskiy"
PETTERSSON  = "Elias Pettersson"
BARKOV      = "Aleksander Barkov"
WILSON      = "Tom Wilson"
STAMKOS     = "Steven Stamkos"
HEDMAN      = "Victor Hedman"


# ---------------------------------------------------------------------------
# §1 — Exact full-name matches
# ---------------------------------------------------------------------------

_S1: list[TC] = [
    TC("full name: Connor McDavid",
       "Connor McDavid skates past the defender",
       players_in={MC_DAVID}),
    TC("full name: Sidney Crosby",
       "Sidney Crosby wins the faceoff deep in the zone",
       players_in={CROSBY}),
    TC("full name: Nathan MacKinnon",
       "Nathan MacKinnon with the shot on goal",
       players_in={MACKINNON}),
    TC("full name: Andrei Vasilevskiy",
       "Andrei Vasilevskiy makes the sprawling pad save",
       players_in={VASILEVSKIY}),
    TC("full name: Ryan Nugent-Hopkins (hyphenated)",
       "Ryan Nugent-Hopkins with a beauty goal on the power play",
       players_in={"Ryan Nugent-Hopkins"}),
    TC("full name: Aleksander Barkov",
       "Aleksander Barkov wins the faceoff for Florida",
       players_in={BARKOV}),
    TC("full name: Leon Draisaitl",
       "Leon Draisaitl snaps it top shelf glove side",
       players_in={DRAISAITL}),
    TC("full name: Elias Pettersson",
       "Elias Pettersson rushes the zone on a two-on-one",
       players_in={PETTERSSON}),
]


# ---------------------------------------------------------------------------
# §2 — Alias → team  ("Leafs", "Avs", "Pens" style)
# ---------------------------------------------------------------------------

_S2: list[TC] = [
    TC("alias: Leafs → TOR",
       "The Leafs win tonight in overtime",
       teams_in={"TOR"}),
    TC("alias: Maple Leafs + Oilers",
       "Maple Leafs beat the Oilers four to one",
       teams_in={"TOR", "EDM"}),
    TC("alias: Avs → COL",
       "Avs come from behind in the third period",
       teams_in={"COL"}),
    TC("alias: Canes → CAR",
       "The Canes shut it down with a dominant defensive effort",
       teams_in={"CAR"}),
    TC("alias: Pens → PIT",
       "Pens advance to the next round of the playoffs",
       teams_in={"PIT"}),
    TC("alias: Bolts → TBL",
       "Bolts score early in the first period on the power play",
       teams_in={"TBL"}),
    TC("alias: Caps → WSH",
       "Caps take the lead with two minutes left on the clock",
       teams_in={"WSH"}),
    TC("alias: Habs → MTL",
       "Habs struggling on the power play again tonight",
       teams_in={"MTL"}),
    TC("alias: Hawks → CHI",
       "Hawks make a line change on the fly",
       teams_in={"CHI"}),
    TC("alias: Sens → OTT",
       "Sens get the power play after a late hit",
       teams_in={"OTT"}),
    TC("alias: Jets → WPG",
       "Jets kill off the penalty and ice the puck",
       teams_in={"WPG"}),
    TC("alias: Preds → NSH",
       "Preds take an early two-goal lead at home",
       teams_in={"NSH"}),
    TC("alias: Isles → NYI",
       "Isles with a strong defensive zone presence",
       teams_in={"NYI"}),
    TC("alias: Wings → DET",
       "Wings score on the power play in the second",
       teams_in={"DET"}),
    TC("alias: Kraken → SEA",
       "Kraken extend the lead going into the third",
       teams_in={"SEA"}),
    TC("alias: Flames → CGY",
       "Flames win the battle along the boards",
       teams_in={"CGY"}),
]


# ---------------------------------------------------------------------------
# §3 — City-only mentions  ("Toronto", "Edmonton", "Tampa Bay", etc.)
# ---------------------------------------------------------------------------

_S3C: list[TC] = [
    TC("city: Toronto → TOR",      "Toronto is absolutely on fire right now",        teams_in={"TOR"}),
    TC("city: Edmonton → EDM",     "Edmonton comes out flying in the second period",  teams_in={"EDM"}),
    TC("city: Vancouver → VAN",    "Vancouver makes a big push late in the game",     teams_in={"VAN"}),
    TC("city: Pittsburgh → PIT",   "Pittsburgh gets on the board first tonight",      teams_in={"PIT"}),
    TC("city: Boston → BOS",       "Boston dominates play in the defensive zone",     teams_in={"BOS"}),
    TC("city: Colorado → COL",     "Colorado is playing their best hockey of the year", teams_in={"COL"}),
    TC("city: Washington → WSH",   "Washington kills off the penalty beautifully",    teams_in={"WSH"}),
    TC("city: Nashville → NSH",    "Nashville takes a two-goal lead at home",         teams_in={"NSH"}),
    TC("city: Tampa Bay → TBL",    "Tampa Bay controls the play on the power play",   teams_in={"TBL"}),
    TC("city: Los Angeles → LAK",  "Los Angeles gets the equalizer late in the third", teams_in={"LAK"}),
    TC("city: San Jose → SJS",     "San Jose forces overtime with a late goal",       teams_in={"SJS"}),
    TC("city: New Jersey → NJD",   "New Jersey is playing very physical tonight",     teams_in={"NJD"}),
    TC("city: St. Louis → STL",    "St. Louis wins the battle along the boards",      teams_in={"STL"}),
    TC("city: Vegas → VGK",        "Vegas makes a statement win on home ice",         teams_in={"VGK"}),
    TC("city: Florida → FLA",      "Florida plays a patient trap game",               teams_in={"FLA"}),
    TC("city: Minnesota → MIN",    "Minnesota gets great goaltending tonight",        teams_in={"MIN"}),
    TC("city: Carolina → CAR",     "Carolina wins the board battle all night long",   teams_in={"CAR"}),
    TC("city: city + alias same sentence",
       "Toronto is up over the Sens in the third period",
       teams_in={"TOR", "OTT"}),
    TC("city: city + player",
       "McDavid puts Edmonton ahead with a power play goal",
       players_in={MC_DAVID}, teams_in={"EDM"}),
]


# ---------------------------------------------------------------------------
# §4 — Surname-only mentions
# ---------------------------------------------------------------------------

_S3: list[TC] = [
    TC("surname: McDavid",
       "McDavid with another unbelievable play tonight",
       players_in={MC_DAVID}),
    TC("surname: Crosby",
       "Crosby wins another faceoff deep in the defensive zone",
       players_in={CROSBY}),
    TC("surname: Ovechkin",
       "Ovechkin is closing in on the all-time scoring record",
       players_in={OVECHKIN}),
    TC("surname: Matthews",
       "Matthews scores his 50th goal of the season",
       players_in={MATTHEWS}),
    TC("surname: Makar",
       "Makar jumps into the rush from the blue line",
       players_in={MAKAR}),
    TC("surname: Kucherov",
       "Kucherov sets up the play perfectly from behind the net",
       players_in={KUCHEROV}),
    TC("surname: Pettersson",
       "Pettersson rushes up the ice on a clean breakaway",
       players_in={PETTERSSON}),
    TC("surname: Rantanen",
       "Rantanen one-timer from the left faceoff circle",
       players_in={RANTANEN}),
    TC("surname: Draisaitl",
       "Draisaitl with a laser beam from the high slot",
       players_in={DRAISAITL}),
    TC("surname: Barkov",
       "Barkov wins every single faceoff in the third period",
       players_in={BARKOV}),
    TC("surname: Vasilevskiy",
       "Vasilevskiy absolutely robbed him on that chance",
       players_in={VASILEVSKIY}),
]


# ---------------------------------------------------------------------------
# §4 — Hardcoded ASR typos
#        Realistic transcription errors from Deepgram or similar STT engines.
# ---------------------------------------------------------------------------

_S4: list[TC] = [
    # ── Player name typos ──────────────────────────────────────────────────
    TC("ASR: Auston→Austin",
       "Austin Matthews with a wrist shot top shelf",
       players_in={MATTHEWS}),
    TC("ASR: Pastrnak→Pasternak",
       "David Pasternak from the right wing scores a beauty",
       players_in={PASTRNAK}),
    TC("ASR: Draisaitl→Draisitle",
       "Leon Draisitle tips it past the goalie",
       players_in={DRAISAITL}),
    TC("ASR: Draisaitl→Draiseitl",
       "Leon Draiseitl wins the race for the puck",
       players_in={DRAISAITL}),
    TC("ASR: MacKinnon→McKinnon",
       "Nathan McKinnon at full speed up the right wing",
       players_in={MACKINNON}),
    TC("ASR: Kucherov→Kucherow",
       "Nikita Kucherow intercepts the cross-ice pass",
       players_in={KUCHEROV}),
    TC("ASR: Vasilevskiy→Vasilevsky",
       "Andrei Vasilevsky denies the shot with the right pad",
       players_in={VASILEVSKIY}),
    TC("ASR: Pettersson→Petterson (one t)",
       "Elias Petterson rushes up the ice with real speed",
       players_in={PETTERSSON}),
    TC("ASR: Tkachuk→Tkatchuk",
       "Brady Tkatchuk causes traffic in front of the net",
       players_in={B_TKACHUK}),
    TC("ASR: Point→Pointe",
       "Brayden Pointe draws a tripping penalty on the play",
       players_in={POINT}),
    TC("ASR: Rantanen→Rantainen",
       "Mikko Rantainen with a brilliant one-touch pass",
       players_in={RANTANEN}),
    TC("ASR: Marner→Mahner (consonant drop)",
       "Mitch Mahner threads the needle on the cross-ice feed",
       players_in={MARNER}),
    TC("ASR: Barkov→Barkoff",
       "Aleksander Barkoff wins it in overtime for Florida",
       players_in={BARKOV}),
    # ── Team name typos ────────────────────────────────────────────────────
    TC("ASR: Leafs→Maple Leaves",
       "The Maple Leaves win the game in regulation tonight",
       teams_in={"TOR"}),
    TC("ASR: Avalanche→Avalanch",
       "Avalanch sweep the series convincingly at home",
       teams_in={"COL"}),
    TC("ASR: Predators→Predaters",
       "The Predaters are up by two goals after two periods",
       teams_in={"NSH"}),
    TC("ASR: Canadiens→Canadians",
       "The Canadians score a big goal on the power play",
       teams_in={"MTL"}),
    TC("ASR: Oilers→Oylers",
       "The Oylers take the lead late in the second period",
       teams_in={"EDM"}),
    TC("ASR: Penguins→Penguings (extra g)",
       "Penguings tie it up with under a minute to play",
       teams_in={"PIT"}),
    TC("ASR: Lightning→Lighning (drop t)",
       "The Lighning power play is clicking on all cylinders",
       teams_in={"TBL"}),
]


# ---------------------------------------------------------------------------
# §5 — Programmatically generated char-level mutations
#        Each tuple: (description, transcript_with_mutated_name, expected_id)
#        Mutation types: swap adjacent chars, double a char, drop interior char.
#        Full names used so the 2-gram pass (threshold 82) provides coverage.
# ---------------------------------------------------------------------------

_MUTATION_SPECS: list[tuple[str, str, str]] = [
    # ── Swap adjacent characters ───────────────────────────────────────────
    ("swap: Connor→Connro",
     "Connro McDavid makes a great move",              MC_DAVID),
    ("swap: McDavid id→di",
     "Connor McDavdi steps around the defenceman",     MC_DAVID),
    ("swap: Crosby sb→bs",
     "Sidney Crosyb breaks in alone on goal",          CROSBY),
    ("swap: Kucherov ro→or",
     "Nikita Kucheorv fires from the left dot",        KUCHEROV),
    ("swap: Rantanen ne→en",
     "Mikko Rantaenn rips a one-timer off the post",   RANTANEN),
    ("swap: Draisaitl ai→ia",
     "Leon Draiasitl sets up the tap-in goal",         DRAISAITL),
    ("swap: Matthews ew→we",
     "Auston Matthwes drives the net hard",            MATTHEWS),
    ("swap: Pettersson ss→ss (oe→eo)",
     "Elias Petteorsson walks in and shoots",          PETTERSSON),
    # ── Double a character ─────────────────────────────────────────────────
    ("double: Makar a→aa",
     "Cale Maakar rushes through the neutral zone",    MAKAR),
    ("double: Crosby s→ss",
     "Sidney Crossby wins the draw in the corner",     CROSBY),
    ("double: McDavid c→cc",
     "Connor MccDavid goes end to end again",          MC_DAVID),
    ("double: Pettersson t→ttt",
     "Elias Petttersson on the partial breakaway",     PETTERSSON),
    ("double: Vasilevskiy l→ll",
     "Andrei Vasillevskiy denies the rebound",         VASILEVSKIY),
    # ── Drop one interior character ─────────────────────────────────────────
    ("drop: Vasilevskiy 2nd i→Vaslevskiy",
     "Andrei Vaslevskiy with the glove save",          VASILEVSKIY),
    ("drop: Draisaitl 2nd a→Draisitl",
     "Leon Draisitl wins the zone battle cleanly",     DRAISAITL),
    ("drop: Pettersson one t→Petersson",
     "Elias Petersson on the clean breakaway chance",  PETTERSSON),
    ("drop: MacKinnon 2nd n→MacKinon",
     "Nathan MacKinon fires a rocket from the point",  MACKINNON),
    ("drop: Kucherov u→Kcherov (with first name)",
     "Nikita Kcherov finishes off the two-on-one",     KUCHEROV),
]

_S5: list[TC] = [
    TC(
        name=f"generated: {desc}",
        transcript=transcript,
        players_in={pid},
    )
    for desc, transcript, pid in _MUTATION_SPECS
]


# ---------------------------------------------------------------------------
# §6 — Multi-entity sentences
# ---------------------------------------------------------------------------

_S6: list[TC] = [
    TC("multi: McDavid + Draisaitl + Oilers",
       "McDavid and Draisaitl power the Oilers with two goals each tonight",
       players_in={MC_DAVID, DRAISAITL},
       teams_in={"EDM"}),
    TC("multi: Matthews + Marner + Toronto",
       "Matthews scores and Marner picks up the assist for Toronto",
       players_in={MATTHEWS, MARNER},
       teams_in={"TOR"}),
    TC("multi: Crosby + Ovechkin + Wilson",
       "Crosby and Ovechkin face off while Wilson applies pressure along the boards",
       players_in={CROSBY, OVECHKIN, WILSON}),
    TC("multi: Avs vs Oilers (team aliases)",
       "The Avs beat the Oilers four to two in a physical game",
       teams_in={"COL", "EDM"}),
    TC("multi: Kucherov + Stamkos + Bolts",
       "Kucherov feeds Stamkos on the power play for the Bolts",
       players_in={KUCHEROV, STAMKOS},
       teams_in={"TBL"}),
    TC("multi: MacKinnon + Rantanen + Avalanche",
       "MacKinnon sets up Rantanen and the Avalanche retake the lead",
       players_in={MACKINNON, RANTANEN},
       teams_in={"COL"}),
    TC("multi: Hedman + Vasilevskiy + Lightning",
       "Victor Hedman leads the rush as Vasilevskiy keeps the Lightning in it",
       players_in={HEDMAN, VASILEVSKIY},
       teams_in={"TBL"}),
]


# ---------------------------------------------------------------------------
# §7 — Edge cases / false-positive guard
# ---------------------------------------------------------------------------

_KNOWN_PLAYERS = {MC_DAVID, CROSBY, MATTHEWS, KUCHEROV, MAKAR, DRAISAITL}
_KNOWN_TEAMS   = {"TOR", "EDM", "COL", "TBL", "WSH"}

_S7: list[TC] = [
    TC("edge: empty string",
       "",
       players_out=_KNOWN_PLAYERS,
       teams_out=_KNOWN_TEAMS),
    TC("edge: whitespace only",
       "   \t\n  ",
       players_out=_KNOWN_PLAYERS,
       teams_out=_KNOWN_TEAMS),
    TC("edge: no hockey content — weather sentence",
       "the weather is really nice and sunny outside today",
       players_out=_KNOWN_PLAYERS,
       teams_out=_KNOWN_TEAMS),
    TC("edge: generic sports sentence (no NHL names)",
       "the quarterback threw a touchdown pass in the fourth quarter",
       players_out=_KNOWN_PLAYERS,
       teams_out=_KNOWN_TEAMS),
    TC("edge: numbers only",
       "one two three four five six seven eight nine ten",
       players_out={MC_DAVID, CROSBY},
       teams_out={"TOR", "EDM"}),
]


# ---------------------------------------------------------------------------
# All sections in display order
# ---------------------------------------------------------------------------

SECTIONS: list[tuple[str, list[TC]]] = [
    ("§1  Exact full names     ", _S1),
    ("§2  Aliases              ", _S2),
    ("§3  City names           ", _S3C),
    ("§4  Surname only         ", _S3),
    ("§5  ASR typos            ", _S4),
    ("§6  Generated typos      ", _S5),
    ("§7  Multi-entity         ", _S6),
    ("§8  Edge cases           ", _S7),
]


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

async def _run_all(extractor: Extractor) -> tuple[int, int]:
    passed = failed = 0

    for heading, cases in SECTIONS:
        print(f"\n{heading}")
        print("─" * 46)
        for tc in cases:
            result  = await extractor.extract_entities(tc.transcript)
            p_set   = set(result["players"])
            t_set   = set(result["teams"])
            errors: list[str] = []

            for player in tc.players_in:
                if player not in p_set:
                    errors.append(f"    missing player  {player!r}")
            for abbrev in tc.teams_in:
                if abbrev not in t_set:
                    errors.append(f"    missing team    {abbrev!r}")
            for player in tc.players_out:
                if player in p_set:
                    errors.append(f"    false-pos player {player!r}")
            for abbrev in tc.teams_out:
                if abbrev in t_set:
                    errors.append(f"    false-pos team   {abbrev!r}")

            if errors:
                failed += 1
                print(f"  FAIL  {tc.name}")
                for e in errors:
                    print(e)
                print(f"        transcript : {tc.transcript!r}")
                print(f"        players    : {sorted(p_set)}")
                print(f"        teams      : {sorted(t_set)}")
            else:
                passed += 1
                print(f"  pass  {tc.name}")

    return passed, failed


if __name__ == "__main__":
    _extractor = Extractor()

    total_cases = sum(len(cases) for _, cases in SECTIONS)
    print(f"Running {total_cases} tests across {len(SECTIONS)} sections…")

    _passed, _failed = asyncio.run(_run_all(_extractor))
    total = _passed + _failed

    print(f"\n{'=' * 46}")
    print(f"  {_passed}/{total} passed", end="")
    if _failed:
        print(f"  —  {_failed} FAILED ✗")
        sys.exit(1)
    else:
        print("  —  all good ✓")
