from pydantic import BaseModel , Field , ConfigDict
from typing import Optional
from bson import ObjectId

config = ConfigDict(
    arbitrary_types_allowed=True,
    json_encoders={ObjectId: str}
)

class SiteData(BaseModel):

    model_config : config 

    keywordId : ObjectId
    siteUrl : str
    content : str

class SiteDataOut(SiteData):
    id : str = Field(alias="_id")