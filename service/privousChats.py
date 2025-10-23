from model.keyword import keyword_collection
from bson import ObjectId

aggregate = [
    {
        '$lookup': {
            'from': 'sitesData', 
            'localField': '_id', 
            'foreignField': 'keywordId', 
            'as': 'sitesData'
        }
    }, {
        '$lookup': {
            'from': 'summary', 
            'localField': '_id', 
            'foreignField': 'keywordId', 
            'as': 'summary'
        }
    }, {
        '$group': {
            '_id': '$_id', 
            'keyword': {
                '$first': '$keyword'
            }, 
            'siteDomain': {
                '$first': '$siteDomain'
            }, 
            'urls': {
                '$first': '$urls'
            }, 
            'content': {
                '$first': '$sitesData.content'
            }, 
            'summary': {
                '$first': {
                    '$arrayElemAt': [
                        '$summary.summary', 0
                    ]
                }
            }
        }
    }
]


async def getAllDetailsById(id):
    print(id)
    try : 
         result = await keyword_collection.aggregate(aggregate).to_list(length=None)
    except Exception as e:
        print(e)
    print("Aggregate result")

    # for doc in result :
    #     doc["_id"] = str(doc["_id"])
    # print(result)
    return result[0]


async def getAllPreviousKeywords():
    
    try : 
        result = await keyword_collection.find().to_list(length=None)
    except Exception as e:
        print(e)
    # for doc in result :
    #     doc["_id"] = str(doc["_id"])
    print("result")
    print(result)
    return result

