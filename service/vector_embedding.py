import voyageai
from dotenv import load_dotenv
import time

load_dotenv("./../.env")


def generate_embeddings(data):
    """
    Generate embeddings for a list of text items using VoyageAI.
    Each item should be a dict with 'text', 'id', and 'type'.
    """
    try:
        
        vo = voyageai.Client()

        
        result = vo.embed(data, model="voyage-3.5")

        # print(result.embeddings[0])
        
        return result.embeddings[0]
    except Exception as error:
        print("Error occurred while generating embeddings!")
        raise error
