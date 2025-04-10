from typing import Dict, List, Optional
from datetime import datetime, date
from dataclasses import dataclass
from enum import Enum

class CardCondition(Enum):
    RAW = "Raw"
    PSA_10 = "PSA 10"
    PSA_9 = "PSA 9"
    SGC_10 = "SGC 10"
    SGC_9_5 = "SGC 9.5"
    SGC_9 = "SGC 9"
    BGS_10 = "BGS 10"
    BGS_9_5 = "BGS 9.5"
    BGS_9 = "BGS 9"
    
    @classmethod
    def from_string(cls, condition_str: str) -> 'CardCondition':
        """Convert a string to a CardCondition enum value."""
        try:
            return cls(condition_str)
        except ValueError:
            return cls.RAW  # Default to RAW if condition not found

@dataclass
class Card:
    player_name: str
    year: str
    card_set: str
    card_number: str
    variation: str
    condition: CardCondition
    purchase_price: float
    purchase_date: datetime
    current_value: float
    last_updated: datetime
    notes: str
    photo: str
    roi: float
    tags: List[str]

    @classmethod
    def from_dict(cls, data: Dict) -> 'Card':
        # Handle tags consistently
        tags = data.get('tags', [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
        elif not isinstance(tags, list):
            tags = []

        # Handle dates
        try:
            purchase_date = datetime.fromisoformat(data.get('purchase_date', datetime.now().isoformat()))
        except ValueError:
            purchase_date = datetime.now()

        try:
            last_updated = datetime.fromisoformat(data.get('last_updated', datetime.now().isoformat()))
        except ValueError:
            last_updated = datetime.now()

        # Handle photo data
        photo = data.get('photo', '')
        if not photo:
            photo = "https://placehold.co/300x400/e6e6e6/666666.png?text=No+Card+Image"
        elif isinstance(photo, str):
            if not photo.startswith('data:image') and not photo.startswith('http'):
                photo = "https://placehold.co/300x400/e6e6e6/666666.png?text=No+Card+Image"
        else:
            photo = "https://placehold.co/300x400/e6e6e6/666666.png?text=No+Card+Image"

        return cls(
            player_name=data.get('player_name', ''),
            year=data.get('year', ''),
            card_set=data.get('card_set', ''),
            card_number=data.get('card_number', ''),
            variation=data.get('variation', ''),
            condition=CardCondition.from_string(str(data.get('condition', 'Raw'))),
            purchase_price=float(data.get('purchase_price', 0.0)),
            purchase_date=purchase_date,
            current_value=float(data.get('current_value', 0.0)),
            last_updated=last_updated,
            notes=data.get('notes', ''),
            photo=photo,
            roi=float(data.get('roi', 0.0)),
            tags=tags
        )

    def to_dict(self):
        """Convert card to dictionary format"""
        return {
            'player_name': self.player_name,
            'year': self.year,
            'card_set': self.card_set,
            'card_number': self.card_number,
            'variation': self.variation,
            'condition': self.condition if isinstance(self.condition, str) else self.condition.value,
            'purchase_price': self.purchase_price,
            'purchase_date': self.purchase_date.strftime('%Y-%m-%d') if isinstance(self.purchase_date, (datetime, date)) else self.purchase_date,
            'current_value': self.current_value,
            'last_updated': self.last_updated.strftime('%Y-%m-%d') if isinstance(self.last_updated, (datetime, date)) else self.last_updated,
            'notes': self.notes,
            'roi': self.roi,
            'tags': self.tags,
            'photo': self.photo
        }

@dataclass
class UserPreferences:
    default_marketplace_fees: float
    default_grading_cost: float
    default_shipping_cost: float

    @classmethod
    def from_dict(cls, data: Dict) -> 'UserPreferences':
        return cls(
            default_marketplace_fees=float(data.get('defaultMarketplaceFees', 12.0)),
            default_grading_cost=float(data.get('defaultGradingCost', 50.0)),
            default_shipping_cost=float(data.get('defaultShippingCost', 15.0))
        )

    def to_dict(self) -> Dict:
        return {
            'defaultMarketplaceFees': self.default_marketplace_fees,
            'defaultGradingCost': self.default_grading_cost,
            'defaultShippingCost': self.default_shipping_cost
        } 