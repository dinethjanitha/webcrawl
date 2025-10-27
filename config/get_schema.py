# config.py

# Defines the structure for the Telecom Knowledge Graph
TELECOM_SCHEMA = {
    "nodes": [
        {
            "label": "Product",
            "description": "Represents a specific telecom product offered (e.g.,  Fiber, PEO TV, SIM, Router, E SIM, Mobile Internet connection)."
        },
        {
            "label": "Plan",
            "description": "Represents a bundled offering or subscription plan (e.g., Postpaid Mobile Plan, Family Fiber Bundle, IDD plan, Prepaid Mobile Plans)."
        },
        {
            "label": "Service",
            "description": "Represents a component service included in products/plans (e.g., PeoTV, International Calling, Internet servie, Local calling)."
        },
        {
            "label": "Customer",
            "description": "Represents a type of customer or segment (e.g., Residential, Business, Genaral )."
        },
        # {
        #     "label": "Location",
        #     "description": "Represents a geographical area of service or mention (e.g., Colombo, Kandy)."
        # },
        # {
        #     "label": "SentimentPost",
        #     "description": "Represents a social media post or comment expressing an opinion about the company or its products."
        # },
        {
            "label": "Price",
            "description": "Represents a monetary value."
        },
        {
            "label": "Speed",
            "description": "Represents a data transfer speed."
        },
        # {
        #     "label": "SentimentValue",
        #     "description": "Represents the category of sentiment (Positive, Negative, Neutral)."
        # }
    ],
    "relationships": [
        {
            "type": "HAS_PRICE",
            "description": "Connects a Product or Plan to its price.",
            # "allowed_nodes": {"source": ["Product", "Plan"], "target": ["Price"]} # Optional
        },
        {
            "type": "HAS_SPEED",
            "description": "Connects an internet Product or Plan to its speed.",
            # "allowed_nodes": {"source": ["Product", "Plan"], "target": ["Speed"]} # Optional
        },
        {
            "type": "INCLUDES",
            "description": "Connects a Product or Plan to a Service it contains.",
            # "allowed_nodes": {"source": ["Product", "Plan"], "target": ["Service"]} # Optional
        },
        # {  
        #     "type": "MENTIONS",
        #     "description": "Connects a SentimentPost to a Product, Service, or the company itself.",
        #     # "allowed_nodes": {"source": ["SentimentPost"], "target": ["Product", "Service", "Plan"]} # Optional
        # },
        # {
        #     "type": "HAS_SENTIMENT",
        #     "description": "Connects a SentimentPost to its expressed sentiment (e.g., Positive, Negative, Neutral).",
        #     # "allowed_nodes": {"source": ["SentimentPost"], "target": ["SentimentValue"]} # Optional
        # },
        # {
        #     "type": "AVAILABLE_IN",
        #     "description": "Connects a Product or Service to a Location where it's available.",
        #     # "allowed_nodes": {"source": ["Product", "Service", "Plan"], "target": ["Location"]} # Optional
        # },
        {
            "type": "TARGETS_CUSTOMER",
            "description": "Connects a Product or Plan to the type of Customer it's intended for.",
            # "allowed_nodes": {"source": ["Product", "Plan"], "target": ["Customer"]} # Optional
        }
    ]
    # "node_properties": {
    #     "Product": ["name", "description"],
    #     "SentimentPost": ["text", "author", "platform", "post_url", "timestamp"]
    # }
}

# GET Schema method
def get_schema():
    return TELECOM_SCHEMA

# if __name__ == "__main__":
#     schema = get_schema()
#     print("Node Labels:", [node['label'] for node in schema['nodes']])
#     print("Relationship Types:", [rel['type'] for rel in schema['relationships']])