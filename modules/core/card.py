from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional

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
    
    def to_dict(self) -> dict:
        """Convert the card to a dictionary format."""
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
        """Create a Card instance from a dictionary."""
        return cls(
            player_name=data['player_name'],
            year=data['year'],
            card_set=data['card_set'],
            card_number=data['card_number'],
            variation=data['variation'],
            condition=CardCondition.from_string(data['condition']),
            purchase_price=float(data['purchase_price']),
            purchase_date=datetime.fromisoformat(data['purchase_date']),
            current_value=float(data['current_value']),
            last_updated=datetime.fromisoformat(data['last_updated']),
            notes=data['notes'],
            photo=data['photo'],
            roi=float(data['roi']),
            tags=data['tags']
        ) 