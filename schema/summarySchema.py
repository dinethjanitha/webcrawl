from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from config.objectIdConterver import PyObjectId


# Custom type that automatically converts ObjectId to string

class Summary(BaseModel):
    keywordId: str
    summary: str

class SummaryOut(Summary):
    id: PyObjectId = Field(alias="_id")  # Auto-converts ObjectId to string
    keywordId: PyObjectId = Field(alias="keywordId")  # Auto-converts ObjectId to string
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )