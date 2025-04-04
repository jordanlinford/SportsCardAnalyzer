from datetime import datetime
from enum import Enum
from typing import List, Optional

class CardCondition(Enum):
    RAW = "Raw"
    PSA_9 = "PSA 9"
    PSA_10 = "PSA 10"

class Card:
    def __init__(
        self,
        player_name: str,
        year: int,
        card_set: str,
        card_number: str,
        variation: str = "",
        condition: CardCondition = CardCondition.RAW,
        purchase_price: float = 0.0,
        purchase_date: datetime = None,
        current_value: float = 0.0,
        last_updated: datetime = None,
        notes: str = "",
        photo: str = "",
        roi: float = 0.0,
        tags: List[str] = None
    ):
        self.player_name = player_name
        self.year = year
        self.card_set = card_set
        self.card_number = card_number
        self.variation = variation
        self.condition = condition
        self.purchase_price = purchase_price
        self.purchase_date = purchase_date or datetime.now()
        self.current_value = current_value
        self.last_updated = last_updated or datetime.now()
        self.notes = notes
        self.photo = photo
        self.roi = roi
        self.tags = tags or []

    def to_dict(self) -> dict:
        """Convert card to dictionary format for storage."""
        return {
            'player_name': self.player_name,
            'year': self.year,
            'card_set': self.card_set,
            'card_number': self.card_number,
            'variation': self.variation,
            'condition': self.condition.value,
            'purchase_price': self.purchase_price,
            'purchase_date': self.purchase_date.isoformat(),
            'current_value': self.current_value,
            'last_updated': self.last_updated.isoformat(),
            'notes': self.notes,
            'photo': self.photo,
            'roi': self.roi,
            'tags': self.tags
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Card':
        """Create card from dictionary format."""
        # Convert string dates back to datetime objects
        if isinstance(data.get('purchase_date'), str):
            data['purchase_date'] = datetime.fromisoformat(data['purchase_date'])
        if isinstance(data.get('last_updated'), str):
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        
        # Convert condition string to enum
        if isinstance(data.get('condition'), str):
            data['condition'] = CardCondition(data['condition'])
        
        return cls(**data) 