from pydantic.functional_validators import BeforeValidator
from typing import Optional, Annotated
from bson import ObjectId

PyObjectId = Annotated[str, BeforeValidator(lambda x: str(x) if isinstance(x, ObjectId) else x)]
