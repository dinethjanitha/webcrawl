# from scrapy.crawler import CrawlerProcess
# from webscrapy.webscrapy.spiders.web_spider import WebSpider
# from webscrapy.webscrapy.spiders.web_spider_new import WebCrawSpider
# from connection.mongocon import mongoCon
from googlesearchmethod.googlesearch import googlesearch
# from scrapy import signals
# from pydispatch import dispatcher
from dotenv import load_dotenv
import os
from urllib.parse import urlparse , urlunparse
from datetime import datetime, timedelta

from fastapi import HTTPException

from langchain_core.prompts import PromptTemplate
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from bson.objectid import ObjectId
from model.keyword import keyword_collection
from model.siteData import siteDataCollection
from model.summary import summaryCollection

# ChromaDB for vector storage (replaces Neo4j)
import chromadb
from chromadb.config import Settings


import subprocess
import sys
import json
import re
import asyncio

load_dotenv("./env")

# Initialize ChromaDB client (persistent storage)
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

# Get or create collection for knowledge graph data
kg_collection = chroma_client.get_or_create_collection(
    name="knowledge_graph",
    metadata={"description": "Web crawl content storage for semantic search"}
)

llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")


# Error tracking for model/agent errors
error_log = []

def trackError(component: str, error_type: str, error_message: str, keywordId: str = None, details: dict = None):
    """
    Track errors that occur during model/agent execution
    
    Args:
        component: Where the error occurred (e.g., 'createKG', 'FullAutoAgent', 'LLM')
        error_type: Type of error (e.g., 'JSONParseError', 'ValidationError', 'TimeoutError')
        error_message: The error message
        keywordId: Associated keyword ID if applicable
        details: Additional details about the error
    """
    error_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "component": component,
        "error_type": error_type,
        "error_message": str(error_message),
        "keywordId": keywordId,
        "details": details or {}
    }
    
    error_log.append(error_entry)
    
    # Print formatted error
    print("\n" + "🔴" * 40)
    print(f" ERROR TRACKED:")
    print(f"   Component: {component}")
    print(f"   Type: {error_type}")
    print(f"   Message: {error_message}")
    if keywordId:
        print(f"   Keyword ID: {keywordId}")
    if details:
        print(f"   Details: {json.dumps(details, indent=2)}")
    print("🔴" * 40 + "\n")
    
    return error_entry


def getErrorLog(component: str = None, keywordId: str = None):
    """
    Retrieve error logs with optional filtering
    
    Args:
        component: Filter by component name
        keywordId: Filter by keyword ID
    
    Returns:
        List of error entries
    """
    filtered_errors = error_log
    
    if component:
        filtered_errors = [e for e in filtered_errors if e["component"] == component]
    
    if keywordId:
        filtered_errors = [e for e in filtered_errors if e["keywordId"] == keywordId]
    
    return filtered_errors


def getErrorSummary():
    """
    Get a summary of all tracked errors
    
    Returns:
        Dictionary with error statistics and recent errors
    """
    if not error_log:
        return {
            "total_errors": 0,
            "message": "No errors tracked"
        }
    
    # Count by component
    component_counts = {}
    error_type_counts = {}
    
    for error in error_log:
        comp = error["component"]
        err_type = error["error_type"]
        
        component_counts[comp] = component_counts.get(comp, 0) + 1
        error_type_counts[err_type] = error_type_counts.get(err_type, 0) + 1
    
    return {
        "total_errors": len(error_log),
        "errors_by_component": component_counts,
        "errors_by_type": error_type_counts,
        "recent_errors": error_log[-5:],  # Last 5 errors
        "all_errors": error_log
    }


# Simple content storage for ChromaDB (no complex KG extraction needed)
def saveContentToChromaDB(keywordId: str, content: str, source_urls: list = None):
    """
    Save crawled content directly to ChromaDB for semantic search.
    No complex KG extraction - ChromaDB handles embedding automatically.
    """
    print("\n" + "=" * 80)
    print("STEP: Saving content to ChromaDB...")
    print("=" * 80)
    
    if not content or len(content.strip()) < 10:
        print("⚠️ Content too short, skipping")
        return
    
    content_length = len(content)
    print(f"📊 Content length: {content_length} characters")
    
    try:
        # Split content into reasonable chunks for ChromaDB (max ~8000 chars each)
        chunk_size = 8000
        chunks = []
        
        if content_length <= chunk_size:
            chunks = [content]
        else:
            # Simple sentence-aware chunking
            sentences = re.split(r'(?<=[.!?])\s+', content)
            current_chunk = ""
            
            for sentence in sentences:
                if len(current_chunk) + len(sentence) < chunk_size:
                    current_chunk += sentence + " "
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + " "
            
            if current_chunk:
                chunks.append(current_chunk.strip())
        
        print(f"   Split into {len(chunks)} chunks")
        
        # Prepare documents for ChromaDB
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({
                "keywordId": keywordId,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "source_urls": json.dumps(source_urls or [])
            })
            ids.append(f"{keywordId}_chunk_{i}")
        
        # Upsert to ChromaDB
        print(f"   🚀 Saving {len(documents)} chunks to ChromaDB...")
        kg_collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"   ✅ Successfully saved to ChromaDB!")
        return {"chunks_saved": len(chunks)}
        
    except Exception as e:
        print(f"❌ ChromaDB error: {e}")
        import traceback
        traceback.print_exc()
        raise


# ChromaDB Query Tool - Semantic search on stored content
@tool
def queryKnowledgeGraph(query: str, keywordId: str = None, n_results: int = 10) -> dict:
    """
    Search the stored content using semantic similarity.
    
    Args:
        query: Search query (natural language)
        keywordId: Optional - filter by specific keyword ID
        n_results: Number of results to return (default 10)
    
    Returns:
        Relevant content chunks matching the query
    """
    print("\n" + "=" * 80)
    print("STEP: Querying ChromaDB for relevant content...")
    print("=" * 80)
    print(f"   Query: {query}")
    print(f"   KeywordId filter: {keywordId or 'None'}")

    try:
        # Build where filter if keywordId provided
        where_filter = None
        if keywordId:
            where_filter = {"keywordId": keywordId}
        
        # Query ChromaDB with semantic search
        results = kg_collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        if not results or not results.get("documents") or not results["documents"][0]:
            print("   ⚠️ No results found")
            return {"results": [], "message": "No matching content found"}
        
        # Process results
        processed_results = []
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results.get("distances", [[]])[0]
        
        for i, (doc, meta) in enumerate(zip(documents, metadatas)):
            # Calculate relevance score (1 = most relevant, 0 = least)
            relevance = 1 - distances[i] if i < len(distances) else 0
            
            result = {
                "content": doc,
                "relevance_score": round(relevance, 3),
                "keywordId": meta.get("keywordId", ""),
                "chunk_index": meta.get("chunk_index", 0),
                "total_chunks": meta.get("total_chunks", 1)
            }
            
            # Add source URLs if available
            source_urls = meta.get("source_urls", "[]")
            try:
                result["source_urls"] = json.loads(source_urls)
            except:
                result["source_urls"] = []
            
            processed_results.append(result)
        
        print(f"   ✅ Found {len(processed_results)} relevant content chunks")
        return {"results": processed_results}
        
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ ChromaDB error: {error_msg}")
        return {"error": f"Query error: {error_msg}"}


@tool
def getFullKnowledgeGraph(keywordId: str) -> dict:
    """
    Get all stored content for a specific keyword ID.
    
    Args:
        keywordId: The keyword ID to retrieve content for
    
    Returns:
        All content chunks stored for this keyword
    """
    print("\n" + "=" * 80)
    print(f"STEP: Getting all content for keywordId: {keywordId}")
    print("=" * 80)
    
    try:
        # Query all documents for this keywordId
        all_results = kg_collection.get(
            where={"keywordId": keywordId},
            include=["documents", "metadatas"]
        )
        
        if not all_results or not all_results.get("documents"):
            print("   ⚠️ No content found for this keywordId")
            return {"content": "", "chunks": [], "message": "No content found"}
        
        # Sort chunks by index and combine
        chunks_with_meta = []
        for doc, meta in zip(all_results["documents"], all_results["metadatas"]):
            chunks_with_meta.append({
                "content": doc,
                "chunk_index": meta.get("chunk_index", 0),
                "source_urls": json.loads(meta.get("source_urls", "[]"))
            })
        
        # Sort by chunk index
        chunks_with_meta.sort(key=lambda x: x["chunk_index"])
        
        # Combine all content
        full_content = "\n\n".join([c["content"] for c in chunks_with_meta])
        
        # Get unique source URLs
        all_urls = []
        for chunk in chunks_with_meta:
            all_urls.extend(chunk.get("source_urls", []))
        unique_urls = list(set(all_urls))
        
        print(f"   ✅ Found {len(chunks_with_meta)} chunks, {len(full_content)} total characters")
        return {
            "content": full_content,
            "chunks": chunks_with_meta,
            "total_chunks": len(chunks_with_meta),
            "source_urls": unique_urls
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ Error: {error_msg}")
        return {"error": f"Failed to get content: {error_msg}"}


# Agent for make decision
@tool
def makeDecisionFromKG(query: str, context: str = "") -> str:
    """
    Ask the LLM to analyze knowledge graph data and make a decision.
    
    Args:
        query: The question to answer
        context: Optional context/data from knowledge graph
    """
    reasoning_prompt = f"""
    You are an intelligent analyst helping answer questions based on knowledge graph data.

    Question: {query}
    
    Context/Data:
    {context if context else "No additional context provided."}

    Analyze the information, infer insights, and give a clear, helpful answer.
    If you don't have enough information, say so clearly.
    """

    print("\n" + "=" * 80)
    print("STEP 1.*: Making Decision from KG data...")
    print("=" * 80)

    response = llm.invoke([HumanMessage(content=reasoning_prompt)])
    return response.content


# ⚡ FAST Direct Query - No Agent overhead (single LLM call)
async def fast_query(keywordId: str, user_prompt: str) -> str:
    """
    Fast decision making - bypasses agent for speed.
    1. Query ChromaDB directly
    2. Single LLM call to answer
    
    ~2-5 seconds instead of 15-30 seconds with agent
    """
    print("\n" + "=" * 80)
    print("⚡ FAST QUERY MODE")
    print("=" * 80)
    
    import time
    start_time = time.time()
    
    # Step 1: Query ChromaDB directly (fast - no LLM)
    print("📊 Step 1: Querying ChromaDB...")
    try:
        results = kg_collection.query(
            query_texts=[user_prompt],
            n_results=5,
            where={"keywordId": keywordId},
            include=["documents", "metadatas", "distances"]
        )
        
        if not results or not results.get("documents") or not results["documents"][0]:
            return "No relevant content found for this query."
        
        # Combine relevant content
        documents = results["documents"][0]
        context = "\n\n---\n\n".join(documents[:5])  # Top 5 results
        
        print(f"   ✅ Found {len(documents)} relevant chunks")
        
    except Exception as e:
        print(f"   ❌ ChromaDB error: {e}")
        return f"Error querying content: {str(e)}"
    
    query_time = time.time() - start_time
    print(f"   ⏱️ Query time: {query_time:.2f}s")
    
    # Step 2: Single LLM call to answer (fast model)
    print("🤖 Step 2: Generating answer...")
    llm_start = time.time()
    
    prompt = f"""Based on the following crawled web content, answer the user's question.

USER QUESTION: {user_prompt}

RELEVANT CONTENT:
{context}

INSTRUCTIONS:
- Answer based ONLY on the provided content
- Be concise and helpful
- Use markdown formatting for readability
- If the content doesn't contain the answer, say so clearly

ANSWER:"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        answer = response.content
    except Exception as e:
        print(f"   ❌ LLM error: {e}")
        return f"Error generating answer: {str(e)}"
    
    llm_time = time.time() - llm_start
    total_time = time.time() - start_time
    
    print(f"   ⏱️ LLM time: {llm_time:.2f}s")
    print(f"   ⏱️ Total time: {total_time:.2f}s")
    print("=" * 80)
    
    print("answer")
    print("answer")
    print("answer")
    print("answer")
    print("answer")
    print(answer)

    return answer


async def ReasoningAgent():
    SYSTEM_PROMPT = """
    You are an intelligent AI reasoning agent that answers questions using crawled web content stored in ChromaDB.
    
    Tools available:
    1. queryKnowledgeGraph(query, keywordId, n_results) — Semantic search for relevant content
    2. getFullKnowledgeGraph(keywordId) — Get all content for a specific crawl session
    3. makeDecisionFromKG(query, context) — Analyze data and provide insights
    
    Workflow:
    1. Use queryKnowledgeGraph to search for relevant information based on the user's question
    2. If you need more complete context, use getFullKnowledgeGraph with the keywordId
    3. Use makeDecisionFromKG to analyze the retrieved content and formulate your answer
    
    Tips:
    - Use natural language queries - ChromaDB performs semantic similarity search
    - Filter by keywordId when you know the specific crawl session to query
    - The content returned is the actual crawled web text, use it to answer questions
    - Combine multiple search results for comprehensive answers
    
    Never mention internal keywordId in your responses to users.
    Be helpful, accurate, and provide clear, well-structured answers based on the crawled content.
    """

    tools = [queryKnowledgeGraph, getFullKnowledgeGraph, makeDecisionFromKG]

    agent = create_agent(
        model=llm,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
        checkpointer=InMemorySaver()
    )
    return agent


async def test_decision(keywordId: str , user_prompt:str):
    # Initialize reasoning agent
    agent = await ReasoningAgent()

    print("\n" + "=" * 80)
    print("STEP 1: Start Agent...")
    print("=" * 80)

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

    # print(user_message)
    # Call the agent
    print("Generating Cypher Query for access knowledge graph... ")

    result = await agent.ainvoke({
        "messages": [
            {"role": "user", "content": improved_user_message}
        ]
    },
    config={"configurable": {"thread_id": "thread_1"}
            } 
    )

    # Safely extract output
    output = result.get("output") or result.get("text") or str(result)

    messages_list = result.get("messages", [])

    print("\n" + "=" * 80)
    print("STEP 2: Checking Agent result...")
    print("=" * 80)

    final_content = None
    if messages_list:
        # Get the last message object from the list
        last_message = messages_list[-1]
        
        # Get the actual text content from that message object
        final_content = last_message.content
        print(final_content)
        
        # print("Decision:\n", final_content[0]["text"])

        print("\n" + "=" * 80)
        print("STEP 3: Finalizing...")
        print("=" * 80)
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
                if isinstance(content, list) and content:
                    # It's a list, get the 'text' from the first dictionary
                    final_text = content[0].get('text', 'No "text" key found in content dict')
                
                elif isinstance(content, str):
                    final_text = content
                
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
    
    """Fetch crawl text data by keyword ID (string). Returns all combined text content and saves to ChromaDB for search."""

    print("\n" + "=" * 80)
    print("STEP 5: Getting crawl content and saving to ChromaDB...")
    print("=" * 80)

    now = datetime.utcnow()
    ten_minutes_ago = now - timedelta(minutes=6)
    
    siteDataResults = await siteDataCollection.find({
        'keywordId': ObjectId(keywordId),
        'createdAt': {'$gte': ten_minutes_ago, '$lte': now}
    }).to_list(None)

    content = []
    source_urls = []
    
    for document in siteDataResults:
        if 'content' in document and document['content']:
            content.append(str(document['content']))
            if 'url' in document:
                source_urls.append(document['url'])
    
    print(f"📊 Found {len(content)} documents in database")
    
    if len(content) > 0:
        # Join all content from all documents
        joinAllContent = "\n\n---\n\n".join(content)
        content_length = len(joinAllContent)
        print(f"   Total content length: {content_length} characters")
        print(f"   Preview (first 200 chars): {joinAllContent[:200]}...")
        
        # Save content directly to ChromaDB - no LLM processing needed!
        print(f"\n🚀 Saving content to ChromaDB...")
        try:
            saveContentToChromaDB(keywordId, joinAllContent, source_urls)
            print(f"✅ Content saved to ChromaDB successfully!")
        except Exception as e:
            print(f"❌ Failed to save to ChromaDB: {str(e)}")
            trackError(
                component="getCrawlContent->saveContentToChromaDB",
                error_type=type(e).__name__,
                error_message=str(e),
                keywordId=keywordId,
                details={"content_length": content_length}
            )
        
        return joinAllContent
    else:
        print("⚠️ No content found in database")
        return ""
    

@tool
def createKG(content:str , keywordId:str) -> object:
    """Process content and confirm it's stored in ChromaDB. Content is automatically saved by getCrawlContent."""

    print("\n" + "=" * 80)
    print("STEP 6: Content Processing Confirmation")
    print("=" * 80)
    print(f"🤖 Agent called createKG tool for keywordId: {keywordId}")
    
    # Content is already saved to ChromaDB by getCrawlContent
    # This tool now just confirms the storage and returns status
    
    if not content or len(content.strip()) < 10:
        print("⚠️ Content is empty or too short")
        return {
            "status": "no_content",
            "message": "No content available to process",
            "keywordId": keywordId
        }
    
    content_length = len(content)
    print(f"✅ Content processed: {content_length} characters")
    print(f"   Preview: {content[:200]}...")
    
    # Verify content is in ChromaDB
    try:
        results = kg_collection.get(
            where={"keywordId": keywordId},
            include=["metadatas"]
        )
        doc_count = len(results.get("ids", []))
        print(f"✅ Verified {doc_count} documents in ChromaDB for keywordId: {keywordId}")
        
        return {
            "status": "success",
            "message": f"Content stored and indexed in ChromaDB",
            "keywordId": keywordId,
            "content_length": content_length,
            "documents_stored": doc_count
        }
    except Exception as e:
        print(f"⚠️ Could not verify ChromaDB storage: {str(e)}")
        return {
            "status": "stored",
            "message": "Content was saved (verification failed)",
            "keywordId": keywordId,
            "content_length": content_length
        }


def deleteKGFromChromaDB(keywordId: str):
    """
    Delete all KG data for a specific keywordId from ChromaDB.
    """
    print(f"\n🗑️ Deleting KG data for keywordId: {keywordId}")
    
    try:
        # Get all documents with this keywordId
        results = kg_collection.get(
            where={"keywordId": keywordId},
            include=["metadatas"]
        )
        
        if results and results.get("ids"):
            ids_to_delete = results["ids"]
            kg_collection.delete(ids=ids_to_delete)
            print(f"   ✅ Deleted {len(ids_to_delete)} documents")
            return {"deleted": len(ids_to_delete)}
        else:
            print(f"   ⚠️ No documents found for this keywordId")
            return {"deleted": 0}
            
    except Exception as e:
        print(f"   ❌ Delete error: {str(e)}")
        return {"error": str(e)}


async def MyAgent():
    SYSTEM_PROMPT = """
    You are an intelligent agent that processes and stores crawled web content.
    
    YOUR WORKFLOW (SIMPLE 2-STEP PROCESS):
    1. First, call getCrawlContent(keywordId) to fetch and store the crawled text data
       - This automatically saves content to ChromaDB for semantic search
    2. Then, call createKG(content, keywordId) to confirm storage completion
    
    IMPORTANT RULES:
    - Always use BOTH tools in sequence
    - Pass the keywordId as a STRING (not ObjectId)
    - Pass the full content text to createKG
    - Report when each step is completed
    
    AVAILABLE TOOLS:
    - getCrawlContent(keywordId: str) -> Fetches crawled text AND saves to ChromaDB
    - createKG(content: str, keywordId: str) -> Confirms storage and returns status
    
    Example flow for keywordId "507f1f77bcf86cd799439011":
    1. Call: getCrawlContent("507f1f77bcf86cd799439011")
    2. Receive: "SLT Mobitel offers fiber internet..."
    3. Call: createKG("SLT Mobitel offers fiber internet...", "507f1f77bcf86cd799439011")
    4. Report: "Content stored in ChromaDB successfully"
    """

    checkpointer = InMemorySaver()
    tools = [getCrawlContent, createKG]

    agent = create_agent(
        model=llm,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
        checkpointer=checkpointer
    )

    return agent

# Run Agent
async def FullAutoAgent(keywordId):
    """
    Run agent to create Knowledge Graph with error tracking
    """
    keywordId_str = str(keywordId)
    
    print("\n" + "=" * 80)
    print(f"STEP 5.1: Calling Agents for keywordId: {keywordId_str}")
    print("=" * 80)
    
    try:
        agent_executor = await MyAgent()

        print(f"🤖 Invoking agent with keywordId: {keywordId_str}")
        print(f"   Agent will: 1) Get crawl content, 2) Create KG (with auto-chunking if needed)")

        # Step 1 + 2 + 3: Crawl content → Create KG
        response = await agent_executor.ainvoke(
        {
            "messages": [
                {"role": "user", "content": f"Generate a knowledge graph for keyword ID {keywordId_str}"}
            ]
        },
        config={"configurable": {"thread_id": f"kg_{keywordId_str}"}}
        )

        print(response)
        # Check if response is valid
        if not response or "messages" not in response:
            error_msg = "Agent returned invalid response structure"
            trackError(
                component="FullAutoAgent",
                error_type="InvalidAgentResponse",
                error_message=error_msg,
                keywordId=keywordId_str,
                details={
                    "response_type": type(response).__name__,
                    "response_keys": list(response.keys()) if isinstance(response, dict) else "Not a dict"
                }
            )
            return {
                "status": "failed",
                "reason": error_msg,
                "keywordId": keywordId_str
            }
        
        # Log successful execution
        messages = response.get("messages", [])
        print(f"\n Agent completed successfully with {len(messages)} messages")
        
        return response

    except TimeoutError as e:
        trackError(
            component="FullAutoAgent",
            error_type="TimeoutError",
            error_message=f"Agent execution timed out: {str(e)}",
            keywordId=keywordId_str,
            details={"timeout_duration": "unknown"}
        )
        print(f" Agent timeout for keywordId: {keywordId_str}")
        return {
            "status": "failed",
            "reason": "Agent execution timed out",
            "keywordId": keywordId_str
        }
    
    except Exception as e:
        trackError(
            component="FullAutoAgent",
            error_type=type(e).__name__,
            error_message=str(e),
            keywordId=keywordId_str,
            details={
                "exception_type": type(e).__name__,
                "traceback": __import__('traceback').format_exc()
            }
        )
        print(f" Error in FullAutoAgent: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "failed",
            "reason": str(e),
            "keywordId": keywordId_str
        }


# Stored Keyword in mongoDB
async def storeKeyword(keyword , url_list):

    if  not url_list or len(url_list) == 0:
        mydict = {
            "keyword" : keyword,
            "urls" : url_list,
        } 

    else : 
        mydict = {
            "keyword" : keyword,
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

# Get details with keyword name
async def getKeywordByDomain(url):
    try:
        if not url.startswith(("http://", "https://")):
            url = "http://" + url

        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace("www.", "") 

        result = await keyword_collection.find_one(
            {"keyword": {"$regex": domain, "$options": "i"}}
        )

        return result
        
    except Exception as e:
        print(e)
        return None    
    return result


# Add urls to keyword document
# async def storeRelevantUrls(keywordId):
    
#     try:
#         keywordDetails = await getKeywordById(keywordId)
        
#         keyword = keywordDetails["keyword"]

#         results = googlesearch(keyword)

#         urlList = []

#         for item in results.get("items", []):
#             print(f"Title: {item['title']}")
#             urlList.append(item['link'])
#             print(f"Link: {item['link']}\n")

#         # print(urls_list)

#         updatedValues = await keyword_collection.update_one(
#             {"_id": ObjectId(keywordId)},
#             {"$push": {"urls": {"$each": urlList}}}
#         )
#         print("Updated Values")
#         print(updatedValues)

#         if updatedValues.acknowledged:
#             print("Update successful!")
#             result = keywordId
#             return result    
#         return None
#     except Exception as e:
#         print(e)
#         return None


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

async def exec(keyword , url_list):
    """
    Complete workflow:
    1. Store keyword
    2. Fetch Google search URLs
    3. Crawl URLs (subprocess)
    4. Summarize content (only if crawl succeeds)
    """
    
    # Step 1: Store keyword or add it to existing keyword
    print("\n" + "=" * 80)
    print("STEP 1.1: Check keyword")
    print("=" * 80)
    
    
        
    result = await getKeywordByDomain(keyword)
    skipSum = False
    if not result : 
        print("\n" + "=" * 80)
        print("STEP 1.2: Storing keyword")
        print("=" * 80)
        storedKeyword = await storeKeyword(keyword, url_list)
        storedKeywordId = storedKeyword.inserted_id
        print(f"Keyword stored with ID: {storedKeywordId}")

        # if url_list and len(url_list) > 0:
        #     updatedKey = await storeRelevantUrls(storedKeyword.inserted_id , None)
            
    else : 
        print("Id is founded!")
        print(result["_id"])
        storedKeywordId = result["_id"]
        skipSum = True
        print("Keyword Already founded! Skip creating new keyword id...")
    # Step 2: Get keyword details
    print("\n" + "=" * 80)
    print("STEP 2: Fetching keyword details")
    print("=" * 80)
    resultMongo = await getKeywordById(storedKeywordId)
    keywordId = resultMongo["_id"]
    # Step 3: Fetch Google URLs

    
    # if not url_list or len(url_list) == 0:
        # print("\n" + "=" * 80)
        # print("STEP 3: Fetching Social media data from google search URLs")
        # print("=" * 80)
    #     print("Finding in here!")
    #     await storeRelevantUrls(keywordId)
    

    # if not keywordId:
    #     print("ERROR: Failed to store URLs")
    #     return {"error": "Failed to fetch URLs from Google"}
    
    # Get updated details with URLs
    print("\n" + "=" * 80)
    print("STEP 3: Checking keyword details")
    print("=" * 80)
    updatedDetails = await getKeywordById(keywordId)
    
    # if "urls" not in updatedDetails or not updatedDetails["urls"]:
    #     print("ERROR: No URLs found!")
    #     return {"error": "No URLs found in Google search results"}
    
    url = updatedDetails["keyword"]
    # url_list_search = updatedDetails["urls"]


    urls = [url]
    
    # if url_list_search and len(url_list_search) > 0:
    #     urls += url_list_search
    
    if url_list and len(url_list) > 0:
        print("\n" + "=" * 80)
        print("STEP 3.1: Manual added url fined crawling started with it!")
        print("=" * 80)
        urls += url_list
    
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
    

    print("\n" + "=" * 80)
    print("STEP 5: Start Agentic AI")
    print("=" * 80)

    resultAgent = await FullAutoAgent(keywordId)

    print("------------------------\n Result Agent\n------------------------")
    # print(resultAgent)
    # Step 5: Summarize (only if crawl succeeded)
    print("\n" + "=" * 80)
    print("STEP 6: Generating AI summary")
    print("=" * 80)
    

    if skipSum == False : 
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
    else : 
         return {
            "status": "success",
            "keyword_id": str(keywordId),
            # "urls_crawled": len(urls),
            # "urls" : urls,
            # "summary": finalValue
        }