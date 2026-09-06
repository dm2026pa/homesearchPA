# models.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class SearchCriteria:
    min_price: int = 280000
    max_price: int = 400000
    target_price: int = 380000
    min_bedrooms: int = 3
    min_bathrooms: float = 2.5
    min_total_area_m2: float = 140.0
    min_living_room_m2: float = 42.0
    min_study_m2: float = 15.0
    require_kids_community: bool = True  # OBLIGATORIO

@dataclass
class MatchEvaluation:
    overall_score: int             # 0 to 100
    category_group: str            # "nuevas_estrenar" o "usados_remodelados"
    category_label: str            # "✨ Nueva por Estrenar" o "🔄 Usado o Remodelado"
    cbe_confirmed: bool
    cbe_note: str
    study_confirmed: bool
    study_note: str
    living_room_feasible: bool
    living_room_note: str
    kids_community: bool
    kids_amenities: List[str]
    kids_rating: str
    newness_status: str
    newness_note: str
    price_status: str
    highlights: List[str] = field(default_factory=list)
    verdict: str = ""

@dataclass
class Property:
    id: str
    portal: str
    url: str
    title: str
    price: int
    property_type: str            # "apartamento" o "casa"
    rooms: int
    baths: float
    area_m2: float
    location: str
    description: str
    photo_url: str
    maintenance_fee: Optional[float] = None
    parking_spaces: Optional[int] = None
    year_built: Optional[int] = None
    developer: Optional[str] = None
    delivery_status: Optional[str] = None
    evaluation: Optional[MatchEvaluation] = None

    @property
    def price_per_m2(self) -> float:
        if self.area_m2 > 0 and self.price > 0:
            return round(self.price / self.area_m2, 2)
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        ev = self.evaluation
        return {
            "id": self.id,
            "portal": self.portal,
            "url": self.url,
            "title": self.title,
            "price": self.price,
            "price_formatted": f"${self.price:,.0f}",
            "price_per_m2": self.price_per_m2,
            "property_type": self.property_type,
            "rooms": self.rooms,
            "baths": self.baths,
            "area_m2": self.area_m2,
            "location": self.location,
            "description": self.description,
            "photo_url": self.photo_url,
            "maintenance_fee": self.maintenance_fee,
            "parking_spaces": self.parking_spaces,
            "year_built": self.year_built,
            "developer": self.developer,
            "delivery_status": self.delivery_status,
            "overall_score": ev.overall_score if ev else 0,
            "category_group": ev.category_group if ev else "usados_remodelados",
            "category_label": ev.category_label if ev else "Usado o Remodelado",
            "cbe_confirmed": ev.cbe_confirmed if ev else False,
            "cbe_note": ev.cbe_note if ev else "",
            "study_confirmed": ev.study_confirmed if ev else False,
            "study_note": ev.study_note if ev else "",
            "living_room_feasible": ev.living_room_feasible if ev else False,
            "living_room_note": ev.living_room_note if ev else "",
            "kids_community": ev.kids_community if ev else False,
            "kids_amenities": ev.kids_amenities if ev else [],
            "kids_rating": ev.kids_rating if ev else "",
            "newness_status": ev.newness_status if ev else "",
            "newness_note": ev.newness_note if ev else "",
            "price_status": ev.price_status if ev else "",
            "verdict": ev.verdict if ev else "",
            "highlights": ev.highlights if ev else []
        }
