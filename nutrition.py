"""
nutrition.py
────────────
Looks up per-100g nutrition data from the USDA FoodData Central API.

- Free with a personal key (3 600 req/hr) — set USDA_API_KEY in .env
- Results cached in nutrition_cache.json — each product is only fetched once
- All lookups are best-effort: failures silently fall back to AI estimates

API docs: https://api.nal.usda.gov/fdc/v1
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Optional

import requests

# ── Config ───────────────────────────────────────────────────────────────────

USDA_SEARCH   = "https://api.nal.usda.gov/fdc/v1/foods/search"
CACHE_FILE    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nutrition_cache.json")
REQUEST_DELAY = 0.05   # seconds between calls

_session = requests.Session()
_session.headers.update({"User-Agent": "AldiMealPlanner/1.0"})

# Rate-limit warning shown once per process
_rate_limit_warned = False

def _api_key() -> str:
    """Read key lazily so .env is loaded before first call."""
    return os.environ.get("USDA_API_KEY", "DEMO_KEY")

def _warn_rate_limit() -> None:
    global _rate_limit_warned
    _rate_limit_warned = True
    print(
        "\n⚠️  USDA API rate limit hit. Nutrition values fall back to AI estimates.\n"
        "   Add  USDA_API_KEY=your_key  to your .env file (free at api.nal.usda.gov/signup).\n"
    )

# ── Cache ─────────────────────────────────────────────────────────────────────

def _load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_cache(cache: dict) -> None:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

_cache: dict = _load_cache()

# ── Nutrient extraction ───────────────────────────────────────────────────────

# Preferred data types in priority order (most generic/reliable first)
_PREFERRED_DATA_TYPES = {"Foundation": 0, "SR Legacy": 1, "Survey (FNDDS)": 2, "Branded": 3}

def _score_food(food: dict, query_words: set[str]) -> tuple[int, int, float]:
    """
    Returns (data_type_priority, -word_overlap, -protein_density) for sorting.
    Lower is better so sorted() gives best match first.
    Protein density tiebreaker helps pick lean meats over processed variants.
    """
    dtype    = food.get("dataType", "Branded")
    priority = _PREFERRED_DATA_TYPES.get(dtype, 4)
    desc     = food.get("description", "").lower()
    overlap  = sum(1 for w in query_words if w in desc)
    # Protein density (protein/calorie ratio) as a tiebreaker for meat/poultry
    prot_density = 0.0
    if any(w in query_words for w in ("chicken", "beef", "pork", "fish", "meat", "turkey", "salmon", "tuna")):
        for n in food.get("foodNutrients", []):
            if n.get("nutrientName") == "Protein":
                prot = n.get("value") or 0
                cal_entry = next((x for x in food.get("foodNutrients", [])
                                  if x.get("nutrientName") == "Energy"
                                  and (x.get("unitName") or "").upper() == "KCAL"), None)
                cal = (cal_entry.get("value") or 1) if cal_entry else 1
                prot_density = prot / max(cal, 1)
                break
    return (priority, -overlap, -prot_density)

def _extract_nutrients(food: dict) -> Optional[dict]:
    """
    Pull kcal, protein, fat, carbs per 100g from a USDA food object.
    Explicitly checks unitName == KCAL to avoid kJ confusion.
    """
    result: dict[str, float] = {}
    for n in food.get("foodNutrients", []):
        name = n.get("nutrientName", "")
        unit = (n.get("unitName") or "").upper()
        val  = n.get("value")
        if val is None:
            continue
        if name == "Energy" and unit == "KCAL" and "calories" not in result:
            result["calories"] = float(val)
        elif name == "Protein" and "protein" not in result:
            result["protein"] = float(val)
        elif name == "Total lipid (fat)" and "fat" not in result:
            result["fat"] = float(val)
        elif name == "Carbohydrate, by difference" and "carbs" not in result:
            result["carbs"] = float(val)
    return result if len(result) == 4 else None

# ── Query simplifier ─────────────────────────────────────────────────────────

# German → English translations for common food words
_DE_TO_EN = {
    "milch": "milk", "eier": "eggs", "ei": "egg", "butter": "butter",
    "käse": "cheese", "quark": "quark soft cheese", "joghurt": "yogurt",
    "sahne": "cream", "mehl": "flour", "zucker": "sugar", "reis": "rice",
    "nudeln": "pasta", "pasta": "pasta", "spaghetti": "spaghetti",
    "farfalle": "pasta cooked", "penne": "pasta cooked", "fusilli": "pasta cooked",
    "tagliatelle": "pasta cooked", "rigatoni": "pasta cooked", "öl": "oil", "essig": "vinegar",
    "salz": "salt", "pfeffer": "pepper", "zwiebel": "onion", "knoblauch": "garlic",
    "tomate": "tomato", "kartoffel": "potato", "möhre": "carrot",
    "spinat": "spinach", "brokkoli": "broccoli", "erbsen": "peas",
    "bohnen": "beans", "linsen": "lentils", "kichererbsen": "chickpeas",
    "hähnchen": "chicken breast", "hühnchen": "chicken breast", "rind": "beef",
    "schwein": "pork", "lachs": "salmon raw", "thunfisch": "tuna",
    "brot": "bread", "brötchen": "bread roll", "haferflocken": "oats rolled",
    "müsli": "muesli", "honig": "honey", "marmelade": "jam",
    "schokolade": "chocolate", "nüsse": "nuts", "mandeln": "almonds",
    "walnüsse": "walnuts", "banane": "banana", "apfel": "apple",
    "orange": "orange", "zitrone": "lemon", "ketchup": "ketchup",
    "senf": "mustard", "mayonnaise": "mayonnaise", "soja": "soy",
    "tofu": "tofu", "paprika": "bell pepper", "zucchini": "zucchini",
    "pilze": "mushrooms", "champignons": "mushrooms", "mais": "corn",
    "erbse": "pea", "feta": "feta cheese", "mozzarella": "mozzarella",
}

def _simplify(title: str) -> str:
    """
    Convert a German Aldi product title to a short English search query.

    'HARVEST MOON Bio Basmati-Reis 500g' → 'basmati rice'
    'Speisequark 500 g'                  → 'quark soft cheese'
    """
    t = title.lower()
    # Remove bracketed content and pack sizes
    t = re.sub(r"[\(\[\{][^\)\]\}]*[\)\]\}]", " ", t)
    t = re.sub(r"\b\d+[\.,]?\d*\s*(g|kg|ml|l|cl|st|stück|pack|x)\b", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"[%®™°·]", " ", t)
    # Remove common brand/quality prefixes that add noise
    t = re.sub(r"\b(bio|fairtrade|aldi|harvest moon|gut bio|rio mare|ja!|"
               r"qualitäts|premium|classic|feine|frische|leichte|extra)\b", " ", t, flags=re.IGNORECASE)
    # Replace German words with English equivalents
    # Check both exact match and if the word contains a known German root (compounds)
    words = t.split()
    translated = []
    for w in words:
        clean = re.sub(r"[^a-zäöüß-]", "", w)
        if clean in _DE_TO_EN:
            translated.extend(_DE_TO_EN[clean].split())
        else:
            # Check compound words: "speisequark" contains "quark", "hähnchenbrust" contains "hähnchen"
            matched = False
            for de_word, en_word in _DE_TO_EN.items():
                if len(de_word) >= 4 and de_word in clean:
                    translated.extend(en_word.split())
                    matched = True
                    break
            if not matched and len(clean) > 2:
                translated.append(clean)
    # Deduplicate while preserving order
    seen, unique = set(), []
    for w in translated:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return " ".join(unique[:5]).strip()

# ── Public API ────────────────────────────────────────────────────────────────

def lookup(title: str) -> Optional[dict]:
    """
    Return {calories, protein, fat, carbs} per 100g or None on failure.

    For dry goods that expand when cooked (pasta, rice, legumes), the returned
    values are adjusted to reflect cooked weight — since recipes specify
    qty_used_kg in cooked amounts. Adjustment factors based on USDA data:
      pasta:      dry→cooked ÷ 2.2   (500g dry pasta → ~1100g cooked)
      rice:       dry→cooked ÷ 2.5
      legumes:    dry→cooked ÷ 2.5   (chickpeas, lentils, beans)

    Results are cached on disk across runs.
    """
    cache_key = title.strip().lower()
    if cache_key in _cache:
        return _cache[cache_key]

    # Check hardcoded fallbacks for foods USDA doesn't handle well
    for key, val in _HARDCODED.items():
        if key in cache_key:
            _cache[cache_key] = val
            _save_cache(_cache)
            return val

    query = _simplify(title)
    if not query:
        _cache[cache_key] = None
        return None

    query_words = set(query.lower().split())

    time.sleep(REQUEST_DELAY)
    try:
        resp = _session.get(
            USDA_SEARCH,
            params={
                "query":    query,
                "pageSize": 10,   # fetch more so we can pick best match
                "api_key":  _api_key(),
            },
            timeout=8,
        )
        if resp.status_code == 429:
            if not _rate_limit_warned:
                _warn_rate_limit()
            return None
        resp.raise_for_status()
        foods = resp.json().get("foods", [])
    except Exception:
        return None

    # Sort by (data type priority, word overlap) — best first
    foods_sorted = sorted(foods, key=lambda f: _score_food(f, query_words))

    nutrients = None
    for food in foods_sorted:
        n = _extract_nutrients(food)
        if n is None:
            continue
        cal  = n["calories"]
        prot = n["protein"]
        # Must be in realistic calorie range
        if not (5 <= cal <= 900):
            continue
        # Eggs: raw whole egg is ~155 kcal, ~13g protein — reject custard/pudding matches
        if any(w.startswith("egg") for w in query_words) and prot < 10:
            continue
        nutrients = n
        break   # first passing result wins

    # Adjust dry→cooked for starchy goods
    if nutrients:
        nutrients = _apply_cooked_factor(nutrients, query)

    _cache[cache_key] = nutrients
    _save_cache(_cache)
    return nutrients


# Hardcoded fallbacks for foods USDA doesn't reliably match.
# Values are per 100g, sourced from standard nutrition tables.
_HARDCODED: dict[str, dict] = {
    "quark":      {"calories": 68,  "protein": 12.0, "fat": 0.2, "carbs": 4.1},   # low-fat Magerquark
    "speisequark":{"calories": 68,  "protein": 12.0, "fat": 0.2, "carbs": 4.1},
    "magerquark": {"calories": 68,  "protein": 12.0, "fat": 0.2, "carbs": 4.1},
}
# Nutrient values from USDA are per 100g dry; divide by factor to get per 100g cooked.
_COOKED_FACTORS: list[tuple[tuple[str, ...], float]] = [
    (("pasta", "cooked", "spaghetti", "farfalle", "penne", "fusilli",
      "rigatoni", "tagliatelle", "noodle"), 2.2),
    (("rice", "basmati", "jasmine", "arborio"), 2.5),
    (("chickpea", "lentil", "bean", "legume", "pea"), 2.5),
]

def _apply_cooked_factor(nutrients: dict, query: str) -> dict:
    """Scale dry-weight nutrient values to cooked-weight equivalent."""
    q = query.lower()
    for keywords, factor in _COOKED_FACTORS:
        if any(k in q for k in keywords):
            return {k: round(v / factor, 2) for k, v in nutrients.items()}
    return nutrients


def lookup_batch(titles: list[str], verbose: bool = False) -> dict[str, Optional[dict]]:
    """Look up a list of titles, skipping any already cached."""
    to_fetch = [t for t in titles if t.strip().lower() not in _cache]
    if verbose and to_fetch:
        print(f"   🥗  Fetching nutrition for {len(to_fetch)} products from USDA…")

    results = {t: lookup(t) for t in titles}

    if verbose:
        hits = sum(1 for v in results.values() if v)
        print(f"   ✅  USDA nutrition: {hits}/{len(titles)} resolved")

    return results
