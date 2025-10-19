from typing import Union
from fastapi import FastAPI
from app import exec

app = FastAPI()


@app.get("/")
def test():
    return {"status" : 200}

@app.get("/ok")
def testTwo():
    result = exec()
    return result

@app.get("/test/{id}")
def read(id:int , q: Union[str,None] = None):
    return {"item_id" : id , "q" : q}