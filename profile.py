"""
profile.py
──────────
Stores and manages the user's budget limits and dietary preferences.
Data is persisted to user_profile.json so settings survive between runs.
"""

import json
import os
from dataclasses import dataclass, asdict, field
from typing import Literal

PROFILE_FILE = "user_profile.json"

DietType = Literal["omnivore", "vegetarian", "vegan"]

DIET_EXCLUDED_SUBCATEGORIES: dict[str, list[str]] = {
    "omnivore": [],
    "vegetarian": [
        "TK Fleisch", "Bratwurst & Würstchen", "Fisch- & Fleischsalate",
        "Fisch & Meeresfrüchte", "Geflügel", "Hackfleisch", "Rindfleisch",
        "Schweinefleisch", "Fleischwurst", "Geflügelwurst", "Salami",
        "Schinken", "Streichwurst & Pasteten", "Wurst- & Fleischkonserven",
        "TK Fisch & Meeresfrüchte", "TK Garnelen", "TK Lachs",
        "Fischkonserven", "Fisch- & Fleischersatz",
    ],
    "vegan": [
        # everything vegetarian excludes, plus dairy and eggs
        "TK Fleisch", "Bratwurst & Würstchen", "Fisch- & Fleischsalate",
        "Fisch & Meeresfrüchte", "Geflügel", "Hackfleisch", "Rindfleisch",
        "Schweinefleisch", "Fleischwurst", "Geflügelwurst", "Salami",
        "Schinken", "Streichwurst & Pasteten", "Wurst- & Fleischkonserven",
        "TK Fisch & Meeresfrüchte", "TK Garnelen", "TK Lachs",
        "Fischkonserven", "Fisch- & Fleischersatz",
        "Milch", "Speisequark", "Fruchtjoghurt & Desserts",
        "Naturjoghurt & Skyr", "Sahne, Schmand & Crème fraîche",
        "Butter & Margarine", "Eier",
        "Schnittkäse", "Weichkäse", "Frischkäse", "Feta & Hirtenkäse",
        "Hartkäse & Stückkäse", "Mozzarella", "Ofenkäse",
        "Reibekäse", "Schmelzkäse",
    ],
}


@dataclass
class UserProfile:
    name: str = "User"
    diet: DietType = "omnivore"
    daily_budget_eur: float = 10.0       # max spend per day
    weekly_budget_eur: float = 60.0      # max spend per week
    servings_per_meal: int = 2           # how many people to cook for
    meals_per_day: int = 3               # breakfast / lunch / dinner
    # track how much has been spent this week
    spent_this_week: float = 0.0
    spent_today: float = 0.0

    # ── derived helpers ──────────────────────────────────────────────────────

    @property
    def remaining_today(self) -> float:
        return round(max(0.0, self.daily_budget_eur - self.spent_today), 2)

    @property
    def remaining_this_week(self) -> float:
        return round(max(0.0, self.weekly_budget_eur - self.spent_this_week), 2)

    @property
    def excluded_subcategories(self) -> list[str]:
        return DIET_EXCLUDED_SUBCATEGORIES.get(self.diet, [])

    def budget_per_meal(self) -> float:
        """Equal share of the daily budget across all meals."""
        return round(self.daily_budget_eur / self.meals_per_day, 2)

    def record_spend(self, amount: float) -> None:
        """Call this after confirming a meal plan purchase."""
        self.spent_today = round(self.spent_today + amount, 2)
        self.spent_this_week = round(self.spent_this_week + amount, 2)

    def reset_daily(self) -> None:
        self.spent_today = 0.0

    def reset_weekly(self) -> None:
        self.spent_this_week = 0.0
        self.spent_today = 0.0

    # ── persistence ──────────────────────────────────────────────────────────

    def save(self, path: str = PROFILE_FILE) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=4)
        print(f"💾 Profile saved to {path}")

    @classmethod
    def load(cls, path: str = PROFILE_FILE) -> "UserProfile":
        if not os.path.exists(path):
            print("ℹ️  No profile found — creating a default profile.")
            profile = cls()
            profile.save(path)
            return profile
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    def display(self) -> None:
        print("┌─────────────────────────────────────────┐")
        print(f"│  👤  {self.name:<37}│")
        print(f"│  🥗  Diet          : {self.diet:<21}│")
        print(f"│  👥  Servings/meal : {self.servings_per_meal:<21}│")
        print(f"│  🍽️   Meals/day     : {self.meals_per_day:<21}│")
        print(f"│  💶  Daily budget  : €{self.daily_budget_eur:<20.2f}│")
        print(f"│  📅  Weekly budget : €{self.weekly_budget_eur:<20.2f}│")
        print(f"│  ✅  Spent today   : €{self.spent_today:<20.2f}│")
        print(f"│  ✅  Spent week    : €{self.spent_this_week:<20.2f}│")
        print(f"│  💰  Left today    : €{self.remaining_today:<20.2f}│")
        print(f"│  💰  Left this week: €{self.remaining_this_week:<20.2f}│")
        print("└─────────────────────────────────────────┘")


# ── interactive setup wizard ─────────────────────────────────────────────────

def setup_wizard() -> UserProfile:
    """Walks the user through creating a new profile interactively."""
    print("\n🧙 Welcome to the Budget Meal Planner setup!\n")

    name = input("Your name: ").strip() or "User"

    print("\nDiet type options: omnivore | vegetarian | vegan")
    diet = input("Your diet [omnivore]: ").strip().lower() or "omnivore"
    if diet not in ("omnivore", "vegetarian", "vegan"):
        print("  Unknown diet — defaulting to omnivore.")
        diet = "omnivore"

    try:
        daily = float(input("Daily budget in EUR [10.00]: ").strip() or "10")
    except ValueError:
        daily = 10.0

    try:
        weekly = float(input("Weekly budget in EUR [60.00]: ").strip() or "60")
    except ValueError:
        weekly = 60.0

    try:
        servings = int(input("Servings per meal (number of people) [2]: ").strip() or "2")
    except ValueError:
        servings = 2

    try:
        meals = int(input("Meals per day [3]: ").strip() or "3")
    except ValueError:
        meals = 3

    profile = UserProfile(
        name=name,
        diet=diet,
        daily_budget_eur=daily,
        weekly_budget_eur=weekly,
        servings_per_meal=servings,
        meals_per_day=meals,
    )
    profile.save()
    return profile


if __name__ == "__main__":
    p = setup_wizard()
    p.display()
