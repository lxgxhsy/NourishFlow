from pydantic import BaseModel
from typing import Literal


class Dish(BaseModel):
    name: str
    estimated_calories: int
    added_sugar_level: Literal["low", "medium", "high"]
    gl_level: Literal["low", "medium", "high"]
    protein_g: int
    blood_sugar_friendly: bool
    tags: list[str]
    key_concerns: list[str] = []
    customization_tips: list[str] = []


class Brand(BaseModel):
    brand: str
    category: str
    typical_wait_minutes: int
    lunch_short_score: int
    blood_sugar_strategy: str
    best_choice_for_at_risk: str
    signature_dishes: list[Dish]
