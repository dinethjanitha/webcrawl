from model.keyword import keyword_collection
from model.siteData import siteDataCollection
from bson import ObjectId

async def getKeywordAll():

    keywords = await keyword_collection.find().to_list(length=None)

    print("-----------keywords--------------")
    print(keywords)

    return keywords  # No manual conversion needed!

async def getKeywordById():

    keyword = await keyword_collection.find_one({"_id" : ObjectId('68f485fbe80683cac7fafc93')})

    print("-----------keyword--------------")
    print(keyword)

    return keyword