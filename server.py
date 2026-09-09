"""
server.py  —  FastAPI backend for the Aldi Budget Meal Planner.

POST /generate-plan
  Body: { budget, diet, days, meals_per_day, servings, cuisines,
          weight_kg, height_cm, age, gender, activity_level }
  Returns verified meal plan JSON including per-meal nutrition estimates.
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

from ai_planner import generate, filter_catalog, CatalogItem

app = FastAPI(title="Aldi Budget Meal Planner API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:3000", "http://127.0.0.1:3000",
    ],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# Activity-level multipliers (Harris-Benedict / Mifflin-St Jeor)
ACTIVITY_FACTORS = {
    "sedentary":   1.2,
    "light":       1.375,
    "moderate":    1.55,
    "active":      1.725,
    "very_active": 1.9,
}


class PlanRequest(BaseModel):
    # ── meal plan settings ────────────────────────────────────────────
    budget:        float      = Field(..., gt=0)
    diet:          str        = Field("omnivore")
    days:          int        = Field(3, ge=1, le=7)
    meals_per_day: int        = Field(3, ge=1, le=5)
    servings:      int        = Field(2, ge=1, le=10)
    cuisines:      list[str]  = Field(default_factory=list)
    basket_items:  list[dict] = Field(default_factory=list,
                                      description="Pre-bought basket from /build-basket")

    # ── body metrics (all optional) ────────────────────────────────────
    weight_kg:      Optional[float] = Field(None, gt=0,  le=300)
    height_cm:      Optional[float] = Field(None, gt=50, le=250)
    age:            Optional[int]   = Field(None, ge=10, le=120)
    gender:         Optional[str]   = Field(None)           # "male" | "female"
    activity_level: Optional[str]   = Field("moderate")    # see ACTIVITY_FACTORS


def compute_nutrition_targets(req: PlanRequest) -> tuple[int | None, int | None, float | None]:
    """
    Returns (tdee_kcal, daily_protein_g, bmi) using Mifflin-St Jeor.
    All three are None if body metrics are incomplete.
    """
    if not all([req.weight_kg, req.height_cm, req.age, req.gender]):
        return None, None, None

    w, h, a = req.weight_kg, req.height_cm, req.age

    # Mifflin-St Jeor BMR
    if req.gender.lower() == "male":
        bmr = 10 * w + 6.25 * h - 5 * a + 5
    else:
        bmr = 10 * w + 6.25 * h - 5 * a - 161

    factor = ACTIVITY_FACTORS.get(req.activity_level or "moderate", 1.55)
    tdee   = round(bmr * factor)

    # Protein: 1.6 g/kg bodyweight (evidence-based for general population)
    daily_protein_g = round(w * 1.6)

    # BMI
    bmi = round(w / ((h / 100) ** 2), 1)

    return tdee, daily_protein_g, bmi


class BasketRequest(BaseModel):
    budget: float     = Field(..., gt=0)
    diet:   str       = Field("omnivore")
    days:   int       = Field(3, ge=1, le=7)
    servings: int     = Field(2, ge=1, le=10)


@app.post("/build-basket")
async def build_basket(req: BasketRequest):
    """
    Greedy basket builder.

    Picks one pack of each unique subcategory (cheapest-per-kg first)
    until the budget would be exceeded.  Returns the basket and total cost
    so the user can review before generating the meal plan.
    """
    def _build():
        items = filter_catalog(req.diet)

        # Scale budget: the catalog uses pro-rated costs but the user
        # will literally buy whole packs at Aldi — so we work in pack prices.
        budget = req.budget
        basket: list[dict] = []
        total  = 0.0
        used_subcats: set[str] = set()

        for item in items:
            # One pack per subcategory to maximise variety
            key = item.subcategory or item.category
            if key in used_subcats:
                continue
            if total + item.price_eur > budget:
                continue
            basket.append({
                "title":       item.title,
                "brand":       item.brand,
                "price_eur":   item.price_eur,
                "weight_kg":   item.weight_kg,
                "category":    item.category,
                "subcategory": item.subcategory,
            })
            total = round(total + item.price_eur, 2)
            used_subcats.add(key)

        return {"basket": basket, "total": total, "budget": budget,
                "remaining": round(budget - total, 2), "items": len(basket)}

    return await run_in_threadpool(_build)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate-plan")
async def generate_plan(req: PlanRequest):
    tdee, daily_protein_g, bmi = compute_nutrition_targets(req)
    try:
        # Run the blocking Gemini call in a thread pool — never blocks the event loop
        result = await run_in_threadpool(
            generate,
            budget          = req.budget,
            diet            = req.diet,
            days            = req.days,
            meals_per_day   = req.meals_per_day,
            servings        = req.servings,
            cuisines        = req.cuisines if req.cuisines else None,
            tdee            = tdee,
            daily_protein_g = daily_protein_g,
            basket_items    = req.basket_items if req.basket_items else None,
        )
        result["user_metrics"] = {
            "weight_kg":       req.weight_kg,
            "height_cm":       req.height_cm,
            "age":             req.age,
            "gender":          req.gender,
            "activity_level":  req.activity_level,
            "bmi":             bmi,
            "tdee_kcal":       tdee,
            "daily_protein_g": daily_protein_g,
        }
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
