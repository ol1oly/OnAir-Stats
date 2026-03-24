# test_rapidfuzz_last_name_alias.py
import random
import time
from rapidfuzz import process, fuzz

# --- Step 1: Players and teams with aliases ---
players = [
    "Nikita Kucherov",
    "Tage Thompson",
    "Connor McDavid",
    "Auston Matthews",
    "David Pastrnak"
]

# Generate last name aliases for players
player_aliases = {}
for player in players:
    last_name = player.split()[-1]
    player_aliases[last_name] = player

# Full names + short/alias names for teams
teams = [
    "Tampa Bay Lightning", "Lightning",
    "Toronto Maple Leafs", "Maple Leafs",
    "Boston Bruins", "Bruins",
    "Edmonton Oilers", "Oilers",
    "Buffalo Sabres", "Sabres"
]

# Unified entity list
entity_list = players + list(player_aliases.keys()) + teams

# Mapping aliases to canonical names (players and teams)
alias_to_full = {**player_aliases, **{teams[i+1]: teams[i] for i in range(0, len(teams), 2)}}

# --- Step 2: Function to find all entities in sentence ---
def find_entities(sentence, entity_list, threshold=80):
    words = sentence.lower().split()
    ngrams = []
    for n in range(1, 4):
        for i in range(len(words)-n+1):
            ngrams.append(" ".join(words[i:i+n]))
    
    matches = {}
    for gram in ngrams:
        match, score, _ = process.extractOne(
            gram, entity_list, scorer=fuzz.WRatio
        )
        if score >= threshold:
            # normalize alias → full name
            if match in alias_to_full:
                match = alias_to_full[match]
            matches[match] = max(matches.get(match, 0), score)
    
    return list(matches.keys()) if matches else None

# --- Step 3: Generate misspellings ---
def misspell(name, num=5):
    variants = []
    for _ in range(num):
        chars = list(name.lower())
        op = random.choice(["delete", "swap", "replace", "insert"])
        idx = random.randint(0, len(chars)-1)
        if op == "delete" and len(chars) > 1:
            del chars[idx]
        elif op == "swap" and len(chars) > 1 and idx < len(chars)-1:
            chars[idx], chars[idx+1] = chars[idx+1], chars[idx]
        elif op == "replace":
            chars[idx] = random.choice("abcdefghijklmnopqrstuvwxyz")
        elif op == "insert":
            chars.insert(idx, random.choice("abcdefghijklmnopqrstuvwxyz"))
        variants.append("".join(chars))
    return variants

# --- Step 4: Embed entity in sentence ---
def embed_in_sentence(name_variant, entity_type="player"):
    if entity_type == "player":
        patterns = [
            f"{name_variant} scored a goal",
            f"Amazing goal by {name_variant}",
            f"The team celebrated after {name_variant} scored",
            f"{name_variant} assisted a fantastic play",
            f"Fans cheered as {name_variant} did it"
        ]
    else:
        patterns = [
            f"{name_variant} won the game",
            f"Fans celebrated {name_variant}'s victory",
            f"The match between {name_variant} and rivals was intense",
            f"{name_variant} scored first",
            f"Excitement as {name_variant} dominated"
        ]
    return random.choice(patterns)

# --- Step 5: Generate test sentences ---
test_sentences = []

# Players (full and last name)
for player in players:
    # full name misspellings
    misspellings = misspell(player, num=5)
    for ms in misspellings:
        sentence = embed_in_sentence(ms, "player")
        test_sentences.append((sentence, [player]))
    # last name misspellings
    last_name = player.split()[-1]
    last_name_misspellings = misspell(last_name, num=3)
    for ms in last_name_misspellings:
        sentence = embed_in_sentence(ms, "player")
        test_sentences.append((sentence, [player]))

# Teams
for i in range(0, len(teams), 2):
    full_name = teams[i]
    short_name = teams[i+1]
    misspellings = misspell(full_name, num=3) + misspell(short_name, num=3)
    for ms in misspellings:
        sentence = embed_in_sentence(ms, "team")
        test_sentences.append((sentence, [full_name]))

# Sentences with both player and team
for player in players[:2]:
    for team in teams[::2][:2]:
        sentence = f"{player} scored for {team} in the final period"
        test_sentences.append((sentence, [player, team]))

# Random sentences with no entity
for _ in range(5):
    test_sentences.append(("the weather is bad today", None))
    test_sentences.append(("I had pizza for lunch", None))

# --- Step 6: Run tests and measure time ---
def run_tests():
    start_time = time.time()
    passed, failed = 0, 0
    for sentence, expected in test_sentences:
        result = find_entities(sentence, entity_list)
        # sort for consistent comparison
        result_sorted = sorted(result) if result else None
        expected_sorted = sorted(expected) if expected else None

        if result_sorted == expected_sorted:
            passed += 1
        else:
            failed += 1
            print(f"FAIL: '{sentence}' → {result_sorted} (expected {expected_sorted})")

    elapsed = time.time() - start_time
    print(f"\nMulti-entity Stress Test (last-name support): passed {passed}, failed {failed}")
    print(f"Time taken: {elapsed:.4f} seconds for {len(test_sentences)} sentences")
    print(f"Avg per sentence: {elapsed/len(test_sentences)*1000:.4f} ms")

if __name__ == "__main__":
    run_tests()