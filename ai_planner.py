"""
ai_planner.py
─────────────
Gemini-powered meal plan generator.

Pipeline
────────
  Stage 1 — Catalog Filter
      Load aldi_catalog.json, keep only food categories, apply diet
      exclusions, and cap the list to a token-friendly size by picking
      the cheapest-per-kg representative from every subcategory.

  Stage 2 — Prompt Construction
      Build a structured prompt that gives Gemini:
        • User constraints (diet, days, total budget, servings)
        • Available ingredient list with exact Aldi prices
        • A strict JSON output schema to fill in

  Stage 3 — Gemini API Call
      Send the prompt via google-generativeai and receive the plan.
      Falls back gracefully if the API key is missing (dry-run mode).

  Stage 4 — Budget Math Verification
      Parse the returned JSON, look up each ingredient's price in the
      catalog index, and verify the true total never exceeds the budget.
      Flag any violation and show the corrected numbers.

Usage
─────
  python ai_planner.py                          # uses profile defaults
  python ai_planner.py --days 3 --budget 20    # override inline
  python ai_planner.py --dry-run               # skip API call, show prompt

Environment
───────────
  Set GEMINI_API_KEY in your environment or a .env file:
      GEMINI_API_KEY=your_key_here
"""

from __future__ import annotations

import io
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from typing import Optional

# Suppress SDK deprecation and AFC warnings before any google imports
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*AFC.*")
warnings.filterwarnings("ignore", message=".*google.generativeai.*")
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf-8-sig"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Optional .env support ─────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not required

from profile import UserProfile, DIET_EXCLUDED_SUBCATEGORIES
from nutrition import lookup_batch, _cache as _nutrition_cache

CATALOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aldi_catalog.json")

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — CATALOG FILTER
# ─────────────────────────────────────────────────────────────────────────────

# Only these categories contain food/drink items
FOOD_CATEGORIES = {
    "Alkoholische Getränke",
    "Backwaren, Aufstriche & Cerealien",
    "Backzutaten, Mehl & Zucker",
    "Bio-Produkte",
    "Fairtrade-Produkte",
    "Fleisch & Fisch",
    "Getränke",
    "Grillen",
    "Käse",
    "Konserven & Fertiggerichte",
    "Milchprodukte & Eier",
    "Nudeln, Reis & Hülsenfrüchte",
    "Saucen, Öle & Gewürze",
    "Süßigkeiten & salzige Snacks",
    "Tiefkühlung",
    "Vegetarisch & Vegan",
    "Wochenangebote",
    "Wurst & Aufschnitt",
}

# Max items sent to the AI (keeps prompt within token limits)
MAX_CATALOG_ITEMS = 120


@dataclass
class CatalogItem:
    title: str
    brand: str
    price_eur: float
    weight_kg: float
    price_per_kg: float
    category: str
    subcategory: Optional[str]
    url: str
    # Per-100g nutrition — populated by filter_catalog via USDA lookup.
    # All are None if the lookup failed (falls back to AI estimates).
    calories_per_100g: Optional[float] = None
    protein_per_100g:  Optional[float] = None
    fat_per_100g:      Optional[float] = None
    carbs_per_100g:    Optional[float] = None

    def label(self) -> str:
        """Short display label: 'Brand Title (€X.XX / Ykg)'"""
        brand_prefix = f"{self.brand} " if self.brand else ""
        return f"{brand_prefix}{self.title} (€{self.price_eur:.2f} / {self.weight_kg:.3f}kg)"


def filter_catalog(
    diet: str,
    catalog_path: str = CATALOG_FILE,
    max_items: int = MAX_CATALOG_ITEMS,
) -> list[CatalogItem]:
    """
    Stage 1: Load catalog, keep food-only items, apply diet exclusions,
    deduplicate by subcategory (keep cheapest-per-kg per subcat),
    then return up to max_items sorted cheapest-per-kg first.
    """
    with open(catalog_path, encoding="utf-8") as f:
        raw: list[dict] = json.load(f)

    excluded_subcats = set(DIET_EXCLUDED_SUBCATEGORIES.get(diet, []))

    filtered: list[CatalogItem] = []
    for item in raw:
        # Must have price and weight to be useful
        if not item.get("price_eur") or not item.get("weight_kg"):
            continue
        # Food categories only
        if item.get("category") not in FOOD_CATEGORIES:
            continue
        # Diet exclusions
        if item.get("subcategory") in excluded_subcats:
            continue

        filtered.append(CatalogItem(
            title=item["title"],
            brand=item.get("brand", ""),
            price_eur=item["price_eur"],
            weight_kg=item["weight_kg"],
            price_per_kg=round(item["price_eur"] / item["weight_kg"], 2),
            category=item["category"],
            subcategory=item.get("subcategory"),
            url=item.get("url", ""),
        ))

    # Sort by price-per-kg so the cheapest options bubble to the top
    filtered.sort(key=lambda x: x.price_per_kg)

    # Deduplicate: keep 3 cheapest items per subcategory so the AI has
    # variety but the prompt stays compact
    seen: dict[str, int] = {}
    deduped: list[CatalogItem] = []
    for item in filtered:
        key = item.subcategory or item.category
        seen[key] = seen.get(key, 0)
        if seen[key] < 3:
            deduped.append(item)
            seen[key] += 1

    deduped = deduped[:max_items]
    _enrich_with_nutrition(deduped)
    return deduped


def _enrich_with_nutrition(items: list[CatalogItem]) -> None:
    """
    Populates *_per_100g fields on each CatalogItem from the USDA cache.

    Cached items resolve instantly. Uncached items are fetched in a
    background thread that is stored on the module so generate() can
    join it (wait for completion) before compute_real_nutrition runs.
    The AI call typically takes 10-30s, giving the thread plenty of time
    to finish — join() is usually instant by the time it's called.
    """
    import threading

    uncached_titles = [
        item.title for item in items
        if item.title.strip().lower() not in _nutrition_cache
    ]

    # Apply whatever is already cached right now
    _apply_nutrition(items)

    # Kick off background fetch for uncached items
    if uncached_titles:
        def _bg_fetch():
            lookup_batch(uncached_titles, verbose=False)
            _apply_nutrition(items)   # re-apply with fresh data

        t = threading.Thread(target=_bg_fetch, daemon=True, name="usda-fetch")
        t.start()
        _nutrition_fetch_thread["thread"] = t
    else:
        _nutrition_fetch_thread["thread"] = None


# Module-level slot to hold the background fetch thread
_nutrition_fetch_thread: dict = {"thread": None}


def _wait_for_nutrition_fetch() -> None:
    """Join the background USDA thread if it's still running."""
    t = _nutrition_fetch_thread.get("thread")
    if t is not None and t.is_alive():
        t.join(timeout=30)   # cap at 30s — never block the user indefinitely
    _nutrition_fetch_thread["thread"] = None


def _apply_nutrition(items: list[CatalogItem]) -> None:
    """Apply whatever is currently in the cache to the item list."""
    for item in items:
        data = _nutrition_cache.get(item.title.strip().lower())
        if data:
            item.calories_per_100g = data.get("calories")
            item.protein_per_100g  = data.get("protein")
            item.fat_per_100g      = data.get("fat")
            item.carbs_per_100g    = data.get("carbs")


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — PROMPT CONSTRUCTION
# ─────────────────────────────────────────────────────────────────────────────

OUTPUT_SCHEMA = """{
  "meal_plan": [
    {
      "day": 1,
      "meals": [
        {
          "meal_type": "breakfast" | "lunch" | "dinner",
          "name": "Recipe Name",
          "servings": <integer>,
          "ingredients": [
            {
              "product_title": "<exact title from the ingredient list>",
              "price_eur": <float>,
              "qty_used_kg": <float>,
              "cost_eur": <float>
            }
          ],
          "instructions": [
            "Step 1 ...",
            "Step 2 ..."
          ],
          "meal_cost_eur": <float>,
          "nutrition_per_serving": {
            "calories_kcal": <integer>,
            "protein_g":     <float>,
            "carbs_g":       <float>,
            "fat_g":         <float>
          }
        }
      ],
      "day_total_eur": <float>,
      "day_nutrition": {
        "total_calories_kcal": <integer>,
        "total_protein_g":     <float>,
        "total_carbs_g":       <float>,
        "total_fat_g":         <float>
      }
    }
  ],
  "grand_total_eur": <float>
}"""


def build_prompt(
    items: list[CatalogItem],
    diet: str,
    days: int,
    budget_eur: float,
    servings: int,
    meals_per_day: int,
    cuisines: list[str] | None = None,
    tdee: int | None = None,
    daily_protein_g: int | None = None,
) -> str:
    """
    Stage 2: Assemble the full prompt string.
    """
    ingredient_lines = []
    for i, item in enumerate(items, 1):
        line = (
            f"  {i:>3}. {item.label():<65}"
            f"  [{item.subcategory or item.category}]"
        )
        ingredient_lines.append(line)

    ingredient_block = "\n".join(ingredient_lines)
    budget_per_day   = round(budget_eur / days, 2)

    if meals_per_day == 1:
        meal_labels = "dinner"
    elif meals_per_day == 2:
        meal_labels = "lunch, dinner"
    else:
        meal_labels = "breakfast, lunch, dinner"
        if meals_per_day > 3:
            extras = ", ".join([f"snack {i}" for i in range(1, meals_per_day - 2)])
            meal_labels = f"breakfast, {extras}, lunch, dinner"

    total_meals = days * meals_per_day

    # Cuisine instruction block
    if cuisines and len(cuisines) > 0:
        cuisine_list = ", ".join(cuisines)
        cuisine_block = (
            f"• Cuisine style  : {cuisine_list}\n"
            f"  → Flavour, spice combinations and technique should reflect "
            f"the chosen cuisine(s). Use the available Aldi ingredients creatively "
            f"to approximate authentic dishes from these traditions."
        )
    else:
        cuisine_block = "• Cuisine style  : Any / International"

    # Nutrition target block (only when user profile provided)
    if tdee is not None and daily_protein_g is not None:
        cal_per_meal   = round(tdee / meals_per_day)
        prot_per_meal  = round(daily_protein_g / meals_per_day)
        nutrition_block = (
            f"• Daily calories : {tdee} kcal  (≈ {cal_per_meal} kcal/meal)\n"
            f"• Daily protein  : {daily_protein_g} g  (≈ {prot_per_meal} g/meal)\n"
            f"  → Estimate nutrition per serving for each meal (calories, protein,\n"
            f"    carbs, fat). Aim to distribute targets evenly across the day.\n"
            f"    Nutrition values should reflect the actual ingredients and quantities used."
        )
        nutrition_instruction = (
            f"10. For every meal fill in nutrition_per_serving with estimated kcal, protein_g,\n"
            f"    carbs_g and fat_g per single serving. Also populate day_nutrition with the\n"
            f"    summed daily totals (multiply per-serving values × servings for each meal).\n"
            f"    Target ≈{cal_per_meal} kcal and ≈{prot_per_meal}g protein per meal."
        )
    else:
        nutrition_block = "• Nutrition      : Estimate calories & macros per serving for each meal."
        nutrition_instruction = (
            "10. For every meal fill in nutrition_per_serving with estimated kcal, protein_g,\n"
            "    carbs_g and fat_g per single serving. Also populate day_nutrition with\n"
            "    summed daily totals (per-serving × servings for each meal)."
        )

    prompt = f"""You are a professional budget nutritionist and chef specialising in world cuisines.
Your task is to create a practical, delicious {days}-day meal plan
using ONLY the ingredients listed below — all available at Aldi supermarket.

═══════════════════════════════════════════════════════
CONSTRAINTS
═══════════════════════════════════════════════════════
• Diet type      : {diet}
• Days           : {days}
• Servings/meal  : {servings} people
• Total budget   : €{budget_eur:.2f}  (≈ €{budget_per_day:.2f}/day)
• Meals per day  : {meals_per_day} ({meal_labels})
{cuisine_block}
{nutrition_block}
• HARD RULE      : grand_total_eur MUST be ≤ €{budget_eur:.2f}
• Use pro-rated costs: if a recipe needs 200 g of a 500 g pack,
  cost = (0.200 / 0.500) × pack_price

═══════════════════════════════════════════════════════
AVAILABLE INGREDIENTS  ({len(items)} items)
═══════════════════════════════════════════════════════
{ingredient_block}

═══════════════════════════════════════════════════════
INSTRUCTIONS
═══════════════════════════════════════════════════════
1. Plan {meals_per_day} meals per day × {days} days = {total_meals} meals total.
   Meal types per day (in order): {meal_labels}.
2. Vary the meals — do not repeat the same recipe more than twice.
3. Each meal_cost_eur = sum of ingredient cost_eur values for that meal.
4. Each day_total_eur = sum of its meal_cost_eur values.
5. grand_total_eur = sum of all day_total_eur values.
6. grand_total_eur MUST be ≤ €{budget_eur:.2f}.
7. Use the EXACT product_title strings from the list above.
8. For each meal provide at least 3 clear cooking instruction steps.
9. Respond with ONLY valid JSON matching the schema below — no extra text.
{nutrition_instruction}

═══════════════════════════════════════════════════════
REQUIRED JSON SCHEMA
═══════════════════════════════════════════════════════
{OUTPUT_SCHEMA}
"""
    return prompt


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 3 — GEMINI API CALL
# ─────────────────────────────────────────────────────────────────────────────

MODEL_NAME = "gemini-3.1-flash-lite"


def call_gemini(prompt: str, api_key: str) -> str:
    """
    Stage 3: Send prompt to Gemini, return raw response text.
    Retries up to 4 times with exponential backoff on 503/429.
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise RuntimeError("google-genai is not installed.\nRun:  pip install google-genai")

    import time

    client = genai.Client(api_key=api_key)

    import os as _os, sys as _sys

    max_retries = 4
    for attempt in range(1, max_retries + 1):
        # Suppress the AFC warning per-call via stderr redirect
        _devnull = open(_os.devnull, "w")
        _old_stderr = _sys.stderr
        _sys.stderr = _devnull
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    max_output_tokens=16384,
                ),
            )
            return response.text
        except Exception as e:
            err = str(e)
            if attempt < max_retries and any(c in err for c in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")):
                wait = 2 ** attempt
                print(f"   ⚠️  Attempt {attempt} failed. Retrying in {wait}s...")
                time.sleep(wait)
                continue
            raise
        finally:
            _sys.stderr = _old_stderr
            _devnull.close()


def parse_response(raw: str) -> dict:
    """
    Robustly extract and parse the JSON from a Gemini response.

    Handles markdown fences, complete JSON (fast path), and all forms
    of truncation: mid-string, mid-number, mid-structure.

    Root-cause fix: when closing truncated JSON, the closing tokens
    must be applied in LIFO order (innermost first), not all ] then
    all }. We therefore track an explicit stack of open tokens so we
    can build the correct closer string.
    """
    # 1. Strip markdown fences
    clean = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    start = clean.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model response.")
    clean = clean[start:]

    # 2. Fast path: complete valid JSON
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    # 3. Walk forward tracking string/escape state and an open-token stack.
    #    Record (position, closer_string) at every safe cut-point:
    #    - after a closing }  (outside a string)
    #    - after a closing ]  (outside a string)
    #    - after a closing "  (end of a string value, outside a string)
    #
    #    closer_string is built by reversing the stack and mapping each
    #    open token to its counterpart — this guarantees correct LIFO order.

    in_s  = False
    esc   = False
    stack: list[str] = []   # '{' or '['
    safe_cuts: list[tuple[int, str]] = []  # (pos, closers)

    def make_closers(stk: list[str]) -> str:
        return "".join("}" if c == "{" else "]" for c in reversed(stk))

    for i, ch in enumerate(clean):
        if esc:
            esc = False
            continue
        if in_s:
            if ch == "\\":
                esc = True
            elif ch == '"':
                in_s = False
                safe_cuts.append((i + 1, make_closers(stack)))
            continue
        if   ch == '"':
            in_s = True
        elif ch == '{':
            stack.append("{")
        elif ch == '[':
            stack.append("[")
        elif ch == '}':
            if stack and stack[-1] == "{":
                stack.pop()
            safe_cuts.append((i + 1, make_closers(stack)))
        elif ch == ']':
            if stack and stack[-1] == "[":
                stack.pop()
            safe_cuts.append((i + 1, make_closers(stack)))

    # 4. Try each cut from the end; accept first with non-empty meal_plan
    for pos, closers in reversed(safe_cuts):
        candidate = clean[:pos].rstrip(", \n\r\t")
        fixed = candidate + closers
        try:
            result = json.loads(fixed)
            if isinstance(result, dict) and result.get("meal_plan"):
                return result
        except json.JSONDecodeError:
            continue

    raise ValueError("Could not recover valid JSON with meal_plan from model response.")


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 4 — BUDGET MATH VERIFICATION
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class VerificationResult:
    passed: bool
    ai_total: float           # what the AI claimed
    verified_total: float     # what Python calculated
    budget: float
    violations: list[str]     # list of discrepancy messages


def verify_budget(plan: dict, budget_eur: float) -> VerificationResult:
    """
    Stage 4: Re-calculate every cost figure from the plan data and
    compare against the budget.  The AI's claimed totals are checked
    against Python's arithmetic — catches hallucinated numbers.
    """
    violations: list[str] = []
    verified_grand_total = 0.0
    ai_grand_total = plan.get("grand_total_eur", 0.0)

    for day_obj in plan.get("meal_plan", []):
        day_num = day_obj.get("day", "?")
        verified_day_total = 0.0
        ai_day_total = day_obj.get("day_total_eur", 0.0)

        for meal in day_obj.get("meals", []):
            verified_meal_cost = 0.0
            ai_meal_cost = meal.get("meal_cost_eur", 0.0)

            for ing in meal.get("ingredients", []):
                cost = round(ing.get("cost_eur", 0.0), 4)
                verified_meal_cost += cost

            verified_meal_cost = round(verified_meal_cost, 2)

            # Check meal-level claim
            if abs(verified_meal_cost - ai_meal_cost) > 0.02:
                violations.append(
                    f"Day {day_num} {meal.get('meal_type','?')} '{meal.get('name','?')}': "
                    f"AI claimed €{ai_meal_cost:.2f}, Python says €{verified_meal_cost:.2f}"
                )
            # Use Python's number going forward
            meal["meal_cost_eur"] = verified_meal_cost
            verified_day_total += verified_meal_cost

        verified_day_total = round(verified_day_total, 2)

        if abs(verified_day_total - ai_day_total) > 0.05:
            violations.append(
                f"Day {day_num} total: AI claimed €{ai_day_total:.2f}, "
                f"Python says €{verified_day_total:.2f}"
            )
        day_obj["day_total_eur"] = verified_day_total
        verified_grand_total += verified_day_total

    verified_grand_total = round(verified_grand_total, 2)

    # Budget check
    if verified_grand_total > budget_eur:
        violations.append(
            f"BUDGET EXCEEDED: verified total €{verified_grand_total:.2f} > "
            f"limit €{budget_eur:.2f} (over by €{verified_grand_total - budget_eur:.2f})"
        )

    plan["grand_total_eur"] = verified_grand_total

    return VerificationResult(
        passed=len(violations) == 0,
        ai_total=round(ai_grand_total, 2),
        verified_total=verified_grand_total,
        budget=budget_eur,
        violations=violations,
    )


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 5 — REAL NUTRITION CALCULATION
# ─────────────────────────────────────────────────────────────────────────────

def compute_real_nutrition(plan: dict, items: list["CatalogItem"]) -> int:
    """
    Stage 5: Replace AI-guessed nutrition figures with values calculated
    from USDA per-100g data stored on each CatalogItem.

    Strategy per ingredient:
      - Build a lookup dict:  product_title (lower) → CatalogItem
      - For each ingredient in each meal:
          real_kcal = qty_used_kg * 10 * item.calories_per_100g   (kg→100g = ×10)
          (same for protein, fat, carbs)
      - If ANY ingredient in a meal is missing USDA data, keep the AI
        estimate for that meal unchanged (partial override would be worse
        than a consistent AI estimate).
      - Recompute day_nutrition from the updated meal values.

    Returns the number of meals successfully overwritten with real data.
    """
    # Build title → item map (case-insensitive)
    item_map: dict[str, "CatalogItem"] = {
        it.title.strip().lower(): it for it in items
    }

    overwritten = 0

    for day_obj in plan.get("meal_plan", []):
        day_cals = day_prot = day_carbs = day_fat = 0.0
        day_has_real = True

        for meal in day_obj.get("meals", []):
            servings = max(meal.get("servings", 1), 1)
            meal_cals = meal_prot = meal_carbs = meal_fat = 0.0
            all_resolved = True

            for ing in meal.get("ingredients", []):
                title_key = ing.get("product_title", "").strip().lower()
                qty_kg    = ing.get("qty_used_kg", 0.0) or 0.0
                item      = item_map.get(title_key)

                if (item is None or
                        item.calories_per_100g is None or
                        item.protein_per_100g  is None or
                        item.fat_per_100g      is None or
                        item.carbs_per_100g    is None):
                    all_resolved = False
                    break

                factor     = qty_kg * 10          # convert kg to units of 100g
                meal_cals  += item.calories_per_100g * factor
                meal_prot  += item.protein_per_100g  * factor
                meal_carbs += item.carbs_per_100g    * factor
                meal_fat   += item.fat_per_100g      * factor

            if all_resolved and meal_cals > 0:
                # Overwrite with real per-serving values
                meal["nutrition_per_serving"] = {
                    "calories_kcal": round(meal_cals  / servings),
                    "protein_g":     round(meal_prot  / servings, 1),
                    "carbs_g":       round(meal_carbs / servings, 1),
                    "fat_g":         round(meal_fat   / servings, 1),
                }
                overwritten += 1
                # Accumulate per-person totals for day_nutrition
                # (divide by servings so day total is on the same basis as TDEE target)
                day_cals  += meal_cals  / servings
                day_prot  += meal_prot  / servings
                day_carbs += meal_carbs / servings
                day_fat   += meal_fat   / servings
            else:
                # Keep AI estimate — it's already per-serving, just add it directly
                day_has_real = False
                nut = meal.get("nutrition_per_serving") or {}
                day_cals  += (nut.get("calories_kcal") or 0)
                day_prot  += (nut.get("protein_g")     or 0)
                day_carbs += (nut.get("carbs_g")       or 0)
                day_fat   += (nut.get("fat_g")         or 0)

        # Always recompute day_nutrition from (mix of real + AI) meal values
        day_obj["day_nutrition"] = {
            "total_calories_kcal": round(day_cals),
            "total_protein_g":     round(day_prot,  1),
            "total_carbs_g":       round(day_carbs, 1),
            "total_fat_g":         round(day_fat,   1),
            "source": "real" if day_has_real else "ai_estimated",
        }

    return overwritten

def display_plan(plan: dict, result: VerificationResult) -> None:
    """Pretty-print the verified meal plan."""
    print("\n" + "═" * 65)
    print("  🤖  AI-GENERATED MEAL PLAN  (Aldi Budget Edition)")
    print("═" * 65)

    # Verification banner
    if result.passed:
        print(f"\n  ✅  Budget verification PASSED")
    else:
        print(f"\n  ⚠️   Budget verification found issues:")
        for v in result.violations:
            print(f"       • {v}")

    print(f"\n  💰  AI claimed total   : €{result.ai_total:.2f}")
    print(f"  🔢  Verified total     : €{result.verified_total:.2f}")
    print(f"  📊  Budget limit       : €{result.budget:.2f}")

    for day_obj in plan.get("meal_plan", []):
        day_num = day_obj["day"]
        day_total = day_obj["day_total_eur"]
        print(f"\n{'─' * 65}")
        print(f"  📅  DAY {day_num}  —  Daily spend: €{day_total:.2f}")
        print(f"{'─' * 65}")

        for meal in day_obj.get("meals", []):
            icon = {"breakfast": "🌅", "lunch": "☀️ ", "dinner": "🌙"}.get(
                meal.get("meal_type", ""), "🍽️"
            )
            print(f"\n  {icon}  {meal.get('meal_type','').upper()}: {meal.get('name','')}")
            print(f"      Meal cost: €{meal.get('meal_cost_eur', 0):.2f}  |  "
                  f"Servings: {meal.get('servings', '?')}")

            print("\n      🛒  Ingredients:")
            for ing in meal.get("ingredients", []):
                qty = ing.get("qty_used_kg", 0)
                cost = ing.get("cost_eur", 0)
                title = ing.get("product_title", "?")
                print(f"           {title[:50]:<50}  "
                      f"{qty:.3f}kg  →  €{cost:.2f}")

            print("\n      🍳  Instructions:")
            for i, step in enumerate(meal.get("instructions", []), 1):
                # Word-wrap long steps at 60 chars
                words = step.split()
                line, lines = [], []
                for w in words:
                    if sum(len(x) + 1 for x in line) + len(w) > 60:
                        lines.append(" ".join(line))
                        line = [w]
                    else:
                        line.append(w)
                if line:
                    lines.append(" ".join(line))
                print(f"           {i}. {lines[0]}")
                for cont in lines[1:]:
                    print(f"              {cont}")

    print(f"\n{'═' * 65}")
    print(f"  GRAND TOTAL (verified): €{result.verified_total:.2f} / €{result.budget:.2f}")
    print(f"{'═' * 65}\n")


def save_plan(plan: dict, path: str = "ai_meal_plan.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=4)
    print(f"  💾  Plan saved to {path}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def run(
    days: Optional[int] = None,
    dry_run: bool = False,
    save: bool = True,
) -> None:
    """
    Full pipeline: filter → prompt → call → verify → display.
    Budget is always taken from the user's profile (remaining_this_week).
    When dry_run=True the API call is skipped and only the prompt is shown.
    """
    profile = UserProfile.load()

    days = days or 3
    # Budget always comes from the profile — never overridden by a flag
    budget = profile.remaining_this_week
    servings = profile.servings_per_meal
    meals_per_day = profile.meals_per_day
    diet = profile.diet

    print(f"\n👤 Profile  : {profile.name}  |  Diet: {diet}  |  Servings/meal: {servings}  |  Meals/day: {meals_per_day}")
    print(f"💰 Budget   : €{profile.weekly_budget_eur:.2f} weekly  |  "
          f"Spent: €{profile.spent_this_week:.2f}  |  "
          f"Remaining: €{budget:.2f}")

    print(f"\n🧹 Stage 1: Filtering catalog for diet='{diet}'...")
    items = filter_catalog(diet)
    print(f"   {len(items)} food items selected after filtering & deduplication.")

    print(f"\n📝 Stage 2: Building prompt ({days} days, {meals_per_day} meals/day, €{budget:.2f} budget from profile, {servings} servings)...")
    prompt = build_prompt(items, diet, days, budget, servings, meals_per_day)
    prompt_tokens_est = len(prompt) // 4  # rough estimate
    print(f"   Prompt length: ~{len(prompt)} chars (~{prompt_tokens_est} tokens).")

    if dry_run:
        print("\n" + "─" * 65)
        print("DRY RUN — prompt that would be sent to Gemini:")
        print("─" * 65)
        print(prompt)
        return

    # Stage 3
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print(
            "\n❌ GEMINI_API_KEY not set.\n"
            "   Set it in your environment or a .env file:\n"
            "     GEMINI_API_KEY=your_key_here\n"
            "   Then re-run, or use --dry-run to preview the prompt."
        )
        return

    print(f"\n🤖 Stage 3: Calling Gemini ({MODEL_NAME})...")
    try:
        raw = call_gemini(prompt, api_key)
    except Exception as e:
        print(f"❌ Gemini call failed: {e}")
        return

    print("   Response received. Parsing JSON...")
    try:
        plan = parse_response(raw)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"❌ Could not parse model response as JSON: {e}")
        print("\nRaw response:\n", raw[:2000])
        return

    print("\n🧮 Stage 4: Verifying budget math...")
    result = verify_budget(plan, budget)

    if result.passed:
        print(f"   ✅ All numbers check out. Verified total: €{result.verified_total:.2f}")
    else:
        print(f"   ⚠️  {len(result.violations)} issue(s) found and corrected.")

    print("\n🥗 Stage 5: Applying USDA nutrition data (cache + background fetch)...")
    _wait_for_nutrition_fetch()   # ensure background USDA thread is done
    _apply_nutrition(items)       # re-apply with fully populated cache
    real_count = compute_real_nutrition(plan, items)
    total_meals = sum(len(d.get("meals", [])) for d in plan.get("meal_plan", []))
    print(f"   ✅ {real_count}/{total_meals} meals computed from real data "
          f"({'AI estimates used for remainder' if real_count < total_meals else 'all real'}).")

    display_plan(plan, result)

    if save:
        save_plan(plan)


# ─────────────────────────────────────────────────────────────────────────────
# CLI  (python ai_planner.py [--days N] [--dry-run])
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]
    days_arg: Optional[int] = None
    dry = False

    i = 0
    while i < len(args):
        if args[i] == "--days" and i + 1 < len(args):
            days_arg = int(args[i + 1]); i += 2
        elif args[i] == "--dry-run":
            dry = True; i += 1
        else:
            i += 1

    run(days=days_arg, dry_run=dry)


# ─────────────────────────────────────────────────────────────────────────────
# API-FRIENDLY ENTRY POINT  (used by server.py — returns data, never prints)
# ─────────────────────────────────────────────────────────────────────────────

def generate(
    budget: float,
    diet: str,
    days: int,
    meals_per_day: int,
    servings: int = 2,
    cuisines: list[str] | None = None,
    tdee: int | None = None,
    daily_protein_g: int | None = None,
    basket_items: list[dict] | None = None,
) -> dict:
    """
    Pure-data pipeline.
    If basket_items is provided (from /build-basket), those are used as the
    ingredient list instead of re-running filter_catalog.  This ensures the
    AI only plans meals using products the user actually bought.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    # Use pre-bought basket if provided, otherwise build from catalog
    if basket_items:
        items = []
        for b in basket_items:
            weight = b.get("weight_kg") or 0
            price  = b.get("price_eur") or 0
            if weight <= 0 or price <= 0:
                continue   # skip malformed entries rather than crash on ZeroDivisionError
            items.append(CatalogItem(
                title        = b["title"],
                brand        = b.get("brand", ""),
                price_eur    = price,
                weight_kg    = weight,
                price_per_kg = round(price / weight, 2),
                category     = b.get("category", ""),
                subcategory  = b.get("subcategory"),
                url          = b.get("url", ""),
            ))
        _enrich_with_nutrition(items)
    else:
        items = filter_catalog(diet)

    # For 1-2 day plans use a single call; for longer plans call per day
    # so the response never exceeds the model's output limit.
    BATCH_SIZE = 2
    all_days: list[dict] = []
    all_violations: list[str] = []
    grand_total = 0.0

    day_ranges = []
    for start in range(0, days, BATCH_SIZE):
        day_ranges.append(list(range(start + 1, min(start + BATCH_SIZE, days) + 1)))

    for day_nums in day_ranges:
        batch_days  = len(day_nums)
        day_start   = day_nums[0]
        # Pro-rate the budget across the batch
        batch_budget = round(budget / days * batch_days, 2)

        prompt = build_prompt(
            items, diet, batch_days, batch_budget, servings,
            meals_per_day, cuisines, tdee, daily_protein_g,
        )
        raw  = call_gemini(prompt, api_key)
        plan = parse_response(raw)

        # Renumber days to match the global day index
        for i, day_obj in enumerate(plan.get("meal_plan", [])):
            day_obj["day"] = day_start + i

        result = verify_budget(plan, batch_budget)
        # Wait for USDA background thread then apply real nutrition
        _wait_for_nutrition_fetch()
        _apply_nutrition(items)
        compute_real_nutrition(plan, items)
        all_days.extend(plan.get("meal_plan", []))
        all_violations.extend(result.violations)
        grand_total += result.verified_total

    grand_total = round(grand_total, 2)
    over = grand_total > budget
    if over:
        all_violations.append(
            f"BUDGET EXCEEDED: verified total €{grand_total:.2f} > limit €{budget:.2f}"
        )

    return {
        "verified_total":   grand_total,
        "budget":           budget,
        "violations":       all_violations,
        "meal_plan":        all_days,
        "tdee":             tdee,
        "daily_protein_g":  daily_protein_g,
    }
