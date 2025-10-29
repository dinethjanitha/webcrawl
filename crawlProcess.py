# from scrapy.crawler import CrawlerProcess
# from webscrapy.webscrapy.spiders.web_spider import WebSpider
# from webscrapy.webscrapy.spiders.web_spider_new import WebCrawSpider
# from connection.mongocon import mongoCon
from googlesearchmethod.googlesearch import googlesearch
# from scrapy import signals
# from pydispatch import dispatcher
from dotenv import load_dotenv
import os

from fastapi import HTTPException

from langchain_core.prompts import PromptTemplate
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langchain.agents import create_agent

from bson.objectid import ObjectId
from model.keyword import keyword_collection
from model.siteData import siteDataCollection
from model.summary import summaryCollection

from neo4j import GraphDatabase


import subprocess
import sys
import json
import re

load_dotenv("./env")

URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))

# print(URI)
# print(AUTH)

llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")


# Agent to access neo4j
@tool
def queryNeo4J(cypher_query:str) -> dict:
    """Get KG from Neo4j"""

    print("NeoStart")
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        with driver.session() as session:
            result = session.run(cypher_query)
            records = [record.data() for record in result]
    return records


# Agent for make decision
@tool
def makeDecisionFromKG(query: str) -> str:
    """
    Ask the LLM to make a decision based on knowledge graph data.
    """
    reasoning_prompt = f"""
    You are an intelligent analyst with Neo4j.

    Question: {query}

    Analyze the relationships, infer insights, and give a concise, logical answer.
    """

    print("In here nowwww")

    response = llm.invoke([HumanMessage(content=reasoning_prompt)])
    return response.content


async def ReasoningAgent():
    SYSTEM_PROMPT = """
    You are an intelligent AI reasoning agent connected to a Neo4j Knowledge Graph.
    You can:
    - Generate Cypher queries to retrieve relevant graph data (using fuzzy search where appropriate)
    - Analyze the graph results and make logical or data-driven decisions based on them.

    You have access to these tools:
    1. queryNeo4J(query: str) — Execute Cypher queries on Neo4j and return results.
    2. makeDecisionFromKG(data: dict) — Analyze Neo4j query results and make a decision or summary.

    Rules:
    - Always first use `queryNeo4J` to gather information before making any decision.
    - When forming Cypher queries:
        - Use fuzzy or partial matching (`CONTAINS`, `toLower()`, or regex `=~ '(?i).*<term>.*'`)
        - Match node and relationship names exactly as defined in the KG schema.
        - Never hallucinate labels or relationships that are not in the schema.
    - After retrieving data, use `makeDecisionFromKG` to interpret the results, summarize insights, or provide reasoning.
    - If the question cannot be answered from the graph, say so clearly.

    Example reasoning flow:
    User: "What packages does SLT Mobitel offer?"
    → Step 1: Use `queryNeo4J` with:
        MATCH (c:Company)-[:HAS]->(p:Package)
        WHERE toLower(c.name) CONTAINS toLower("slt mobitel")
        RETURN p.name, p.price
    → Step 2: Use `makeDecisionFromKG` to analyze results and summarize.

    Be clear, structured, and logical in your thought process.
    """


    tools = [queryNeo4J, makeDecisionFromKG]

    agent = create_agent(
        model=llm,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
    )

    
    return agent


async def test_decision(keywordId: str , user_prompt:str):
    # Initialize reasoning agent
    agent = await ReasoningAgent()

    # Prepare user query
    user_message = f"""
    Retrieve data about keywordId '{keywordId}' and decide:
    Task: {user_prompt}

    """

    improved_user_message = f"""
    Task: {user_prompt}

    Data Retrieval Instruction:
    1. Retrieve data about associated with the internal parameter keywordId: '{keywordId}'.
    2. Analyze the retrieved performance data.
    3. Execute the Task described above.
    4. Never mention keywordId in your final output.

    Output Format: Provide the final response, including the analysis and decision, in Markdown (.md) format.
    """

    print(user_message)
    # Call the agent
    result = await agent.ainvoke({
        "messages": [
            {"role": "user", "content": improved_user_message}
        ]
    },
    config={"configurable": {"thread_id": "re_1"}
            } 
    )

    # Safely extract output
    output = result.get("output") or result.get("text") or str(result)

    messages_list = result.get("messages", [])

    final_content = None
    if messages_list:
        # Get the last message object from the list
        last_message = messages_list[-1]
        
        # Get the actual text content from that message object
        final_content = last_message.content
        print(final_content)
        
        # print("Decision:\n", final_content[0]["text"])

        # Assuming 'result' is the variable holding your agent's output

        try:
            # 1. Get the list of messages.
            # The output key is often 'messages', but could be 'output' or 'chat_history'.
            if "messages" in result:
                messages_list = result["messages"]
            elif "output" in result and isinstance(result["output"], list):
                messages_list = result["output"]
            else:
                print("Could not find a 'messages' list in the result.")
                print("Full result keys:", result.keys())
                # Set an empty list to avoid crashing later
                messages_list = []

            # 2. Check if the list is not empty
            if messages_list:
                # Get the last message object
                last_message = messages_list[-1]
                
                # 3. Get the .content attribute
                content = last_message.content
                
                final_text = ""
                
                # 4. Check the type of content and extract text
                
                # --- This handles the format from your last example ---
                if isinstance(content, list) and content:
                    # It's a list, get the 'text' from the first dictionary
                    final_text = content[0].get('text', 'No "text" key found in content dict')
                
                # --- This handles a simple string response ---
                elif isinstance(content, str):
                    final_text = content
                
                # --- This handles other unexpected formats ---
                else:
                    final_text = str(content) # Convert to string as a fallback

                print("--- Final AI Message ---")
                print(final_text)
                
                return {
                    "status" : "success",
                    "message" : final_text
                }
            else:
                print("No messages found in the list.")

                return HTTPException(status_code=404,  detail={
                    "status" : "fail",
                    "details" : "Somethings wrong check terminal for find error" 
                })

        except Exception as e:
            print(f"An error occurred: {e}")
            print("--- Full Agent Result for Debugging ---")
            print(result)
            return HTTPException(status_code=404, detail={
                "status" : "fail",
                "details" : "Somethings wrong check terminal for find error" 
            })
    else:
        # This helps you debug if the agent's output format is different
        print("Error: Could not find 'messages' in the result.")
        print("Full result:", result)
        return  HTTPException(status_code=404,  detail={
                    "status" : "fail",
                    "details" : "Somethings wrong check terminal for find error" 
                })

    # print("Decision:\n", output['messages'].content)



@tool
async def getCrawlContent(keywordId:str) -> str:
    
    """Fetch crawl text data by keyword ID (string). Returns all combined text content for that keyword."""

    siteDataResults = await siteDataCollection.find({'keywordId' : ObjectId(keywordId)}).to_list(length=None)
    
    content = []
    for document in siteDataResults:
        content.append(document['content'])
    print("content")
    print(len(content))
    if len(content) > 0 :
        joinAllContent = "".join(content)
        print(f"Total content length: {len(joinAllContent)} characters")
        return joinAllContent
    else :
        return ""
    

@tool
def createKG(content:str , keywordId:str) -> object:
    """After get crawl content create Knowledge Graph and return Knowledge Graph JSON format """

    prompt_template = """
    You are an expert in extracting structured knowledge from text.

    Input: {crawl_text}

    Task:
    - Identify all nodes (entities) and relationships (edges) mentioned in the text.
    - Output ONLY valid JSON in this format:
    - All letters should be simple letters 

    {{
    "nodes": [  
        {{
        "label": "<NodeLabel>",
        "name": "<NodeName>",
        "properties": {{"key": "value"}}
        }}
    ],
    "edges": [
        {{
        "from": "<SourceNodeName>",
        "type": "<RelationType>",
        "to": "<TargetNodeName>",
        "properties": {{"key": "value"}}
        }}
    ]
    }}
    """


    prompt = PromptTemplate(
        input_variables=["crawl_text"],
        template=prompt_template,
    )

    full_prompt = prompt.format_prompt(
        crawl_text=content
    )

    try:
        print("Exe hereeeeeeeeeeeeeeeeee")
        llm_response = llm.invoke(full_prompt)
    
        clean_text = re.sub(r"^```json\s*|\s*```$", "", llm_response.content.strip())

        json_out = json.loads(clean_text)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Internal server error!")
    
    print(llm_response.content)

    saveKGToNeo4j(keywordId , json_out)
    return json_out


def saveKGToNeo4j(keywordId: str, kg_json: dict):
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        with driver.session() as session:
            try:
                # Delete old graph for this keyword
                session.run("MATCH (n {keywordId: $id}) DETACH DELETE n", {"id": keywordId})

                # Create all nodes
                for node in kg_json["nodes"]:
                    label = node["label"]
                    name = node["name"]
                    properties = node.get("properties", {})
                    properties.update({"name": name, "keywordId": keywordId})
                    prop_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
                    session.run(f"CREATE (n:{label} {{ {prop_str} }})", properties)

                # Create relationships
                for edge in kg_json["edges"]:
                    rel_type = re.sub(r"[^A-Za-z0-9_]", "_", edge["type"]).upper()
                    props = edge.get("properties", {})
                    props["keywordId"] = keywordId
                    props["from"] = edge["from"]
                    props["to"] = edge["to"]

                    session.run(f"""
                        MATCH (a {{name: $from, keywordId: $keywordId}}),
                              (b {{name: $to, keywordId: $keywordId}})
                        CREATE (a)-[r:{rel_type} {{keywordId: $keywordId}}]->(b)
                    """, props)

            except Exception as e:
                print(" Neo4j error:", e)
                raise HTTPException(status_code=500, detail=f"Neo4j error: {e}")


async def MyAgent():
    SYSTEM_PROMPT = """
    You are an intelligent agent that can gather crawl data by keyword and create knowledge graphs automatically.
    You have access to two tools:
    - getCrawlContent: fetches all crawl text for a given keyword ID.
    - createKG: converts raw text into a structured knowledge graph.
    """

    checkpointer = InMemorySaver()
    tools = [getCrawlContent, createKG]

    agent = create_agent(
        model=llm,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
        # checkpointer=checkpointer
    )


    return agent

# Run Agent
async def FullAutoAgent(keywordId: str):
    agent_executor = await MyAgent()

    print("keywordId")
    print(keywordId)

    # Step 1 + 2 + 3: Crawl content → Create KG
    response = await agent_executor.ainvoke(
    {
        "messages": [
            {"role": "user", "content": f"Generate a knowledge graph for keyword ID {keywordId}"}
        ]
    },
    config={"configurable": {"thread_id": "kg_1"}}
    )


    # Step 4: Save to Neo4j
    print("Knowledge Graph saved to Neo4j successfully.")

    return response


# Stored Keyword in mongoDB
async def storeKeyword(keyword , siteDomain):
    mydict = {
        "keyword" : keyword,
        "siteDomain" : siteDomain,
    }
    try:
        x = await keyword_collection.insert_one(mydict) 
        print("---x----") 
        print(x) 
    except Exception as e:
        print(e)
        return None    
    print("xxxxxxxxxxxxxxxxxxxxxx")
    print(x)
    return x


# Get details with keyword ID
async def getKeywordById(id):
    try:
        result = await keyword_collection.find_one({"_id" : ObjectId(id)})
    except Exception as e:
        print(e)
        return None    
    return result


# Add urls to keyword document
async def storeRelevantUrls(keywordId):
    
    try:
        keywordDetails = await getKeywordById(keywordId)
        
        keyword = keywordDetails["keyword"]
        siteDomain = keywordDetails["siteDomain"]

        results = googlesearch(keyword , siteDomain)

        urlList = []

        for item in results.get("items", []):
            print(f"Title: {item['title']}")
            urlList.append(item['link'])
            print(f"Link: {item['link']}\n")

        print(urlList)

        updatedValues = await keyword_collection.update_one({"_id" : ObjectId(keywordId)} , {"$set" : {"urls" : urlList}})
        print("Updated Values")
        print(updatedValues)

        if updatedValues.acknowledged:
            print("Update successful!")
            result = keywordId
            return result    
        return None
    except Exception as e:
        print(e)
        return None


# Crawl web data using subprocess
async def crawlUrls(urls, keywordId):
    """
    Runs the web crawler in a separate subprocess
    Returns: True if successful, False if failed
    """
    python_path = os.path.join(sys.prefix, "Scripts", "python.exe")  # Windows venv
    
    if not os.path.exists(python_path):
        python_path = os.path.join(sys.prefix, "bin", "python")  # Linux/Mac
    
    print("=" * 80)
    print("Starting crawler subprocess")
    print(f"Keyword ID: {keywordId}")
    print(f"Total URLs to crawl: {len(urls)}")
    print("=" * 80)
    
    try:
        # Run web_crawl_runner.py with URLs and keywordId as arguments
        process = subprocess.run(
            [python_path, "web_crawl_runner.py", *urls, str(keywordId)],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            timeout=300  # 5 minutes timeout
        )
        
        print("\n--- Crawler Output ---")
        print(process.stdout)
        
        if process.stderr:
            print("\n--- Crawler Warnings/Errors ---")
            print(process.stderr)
        
        print(f"\n--- Return Code: {process.returncode} ---")
        
        if process.returncode == 0:
            print("SUCCESS: Crawler completed successfully!")
            return True
        else:
            print(f"FAILED: Crawler failed with exit code {process.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("ERROR: Crawler timeout after 5 minutes")
        return False
    except Exception as e:
        print(f"ERROR: Subprocess exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def summarizeUsingAgent(keywordId):

    joinAllContent = None

    print(keywordId)
    try:
        keywordDetails = await keyword_collection.find_one({'_id' : ObjectId(keywordId)})

        siteDataResults = await siteDataCollection.find({'keywordId' : ObjectId(keywordId)}).to_list(length=None)
        print("siteDataResults")
        mainKeyword = keywordDetails['keyword']
        print("mainKeyword")
        print(mainKeyword)
        content = []
        for document in siteDataResults:
            content.append(document['content'])

        print("content")
        print(len(content))
        if len(content) > 0 :
            joinAllContent = "".join(content)
            print(f"Total content length: {len(joinAllContent)} characters")

        openai_key = os.getenv("GOOGLE_API_KEY")

        

        prompt = f"Summarize the following and align that details with this keyword {mainKeyword} **this summarize get word crawl result so mention it in top and not top as provide text show it as crawl we summary results** (using .md style to your response): {joinAllContent if joinAllContent else 'No text found'}"

        print("Prompt length: ", len(prompt))

        

        response = llm.invoke([HumanMessage(content=prompt)])


        # Print the result's content
        print("Summary generated successfully!")
        print(response.content) 

        summaryData = {"keywordId" : ObjectId(keywordId) , "summary" : response.content }

        await summaryCollection.insert_one(summaryData)

        return response.content
    except Exception as e:
        print(f"Summarization error: {e}")
        return None


async def exec(keyword , domain):
    """
    Complete workflow:
    1. Store keyword
    2. Fetch Google search URLs
    3. Crawl URLs (subprocess)
    4. Summarize content (only if crawl succeeds)
    """
    
    # Step 1: Store keyword
    print("\n" + "=" * 80)
    print("STEP 1: Storing keyword")
    print("=" * 80)
    domain = "com"
    storedKeyword = await storeKeyword(keyword, domain)
    print(f"Keyword stored with ID: {storedKeyword.inserted_id}")

    # Step 2: Get keyword details
    print("\n" + "=" * 80)
    print("STEP 2: Fetching keyword details")
    print("=" * 80)
    resultMongo = await getKeywordById(storedKeyword.inserted_id)
    keywordId = resultMongo["_id"]

    # Step 3: Fetch Google URLs
    print("\n" + "=" * 80)
    print("STEP 3: Fetching Google search URLs")
    print("=" * 80)
    # updatedKey = await storeRelevantUrls(storedKeyword.inserted_id)
    
    if not keywordId:
        print("ERROR: Failed to store URLs")
        return {"error": "Failed to fetch URLs from Google"}
    
    # Get updated details with URLs
    updatedDetails = await getKeywordById(keywordId)
    
    # if "urls" not in updatedDetails or not updatedDetails["urls"]:
    #     print("ERROR: No URLs found!")
    #     return {"error": "No URLs found in Google search results"}
    
    url = updatedDetails["keyword"]
    urls = [url]


    print(f"Found URL {updatedDetails["keyword"]}  URLs to crawl")
    # for i, url in enumerate(urls, 1):
    #     print(f"   [{i}] {url}")

    # Step 4: Crawl URLs
    print("\n" + "=" * 80)
    print("STEP 4: Starting web crawl")
    print("=" * 80)
    
    crawl_success = await crawlUrls(urls, keywordId)
    
    if not crawl_success:
        print("ERROR: Crawl failed!")
        return {
            "error": "Web crawl failed",
            "keyword_id": str(keywordId),
            "urls_attempted": len(urls)
        }
    
    resultAgent = await FullAutoAgent(keywordId)

    print("------------------------\n Result Agent\n------------------------")
    print(resultAgent)
    # Step 5: Summarize (only if crawl succeeded)
    print("\n" + "=" * 80)
    print("STEP 5: Generating AI summary")
    print("=" * 80)
    

    finalValue = await summarizeUsingAgent(keywordId)
    if finalValue == None :
        return {
        "status": "Summarization failed!",
    }
    print("\n" + "=" * 80)
    print("WORKFLOW COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    
    return {
        "status": "success",
        "keyword_id": str(keywordId),
        "urls_crawled": len(urls),
        "urls" : urls,
        "summary": finalValue
    }