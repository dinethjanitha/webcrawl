from pydantic import BaseModel , Field , ConfigDict
# from typing import Optional
# from bson import ObjectId
from config.objectIdConterver import PyObjectId

# config = ConfigDict(
#     arbitrary_types_allowed=True,
#     json_encoders={ObjectId: str}
# )

class SiteData(BaseModel):

    # model_config : config 

    keywordId : str
    siteUrl : str
    content : str

class SiteDataOut(SiteData):

    id: PyObjectId = Field(alias="_id")  # Auto-converts ObjectId to string
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )