from typing import Union;
from fastapi import FastAPI;

app = FastAPI()


@app.get("/")
def test():
    return {"status" : 200}

@app.get("/test/{id}")
def read(id:int , q: Union[str,None] = None):
    return {"item_id" : id , "q" : q}