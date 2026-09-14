from pydantic import BaseModel
from typing import Optional, Dict, Any

class ProductBase(BaseModel):
    name: str
    category: str
    barcode: Optional[str] = None
    standard_nutrition: Optional[Dict[str, Any]] = None
    milk_reference: Optional[Dict[str, Any]] = None

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int

    class Config:
        from_attributes = True
