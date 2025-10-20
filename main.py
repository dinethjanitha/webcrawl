from typing import Union
from fastapi import FastAPI
from crawlProcess import exec  # Assuming these are in other files
# from testdb import getKeywordAll , getKeywordById # Assuming these are in other files
# from schema.keywordSchema import Keyword , KeywordOut # Assuming these are in other files
import subprocess
import os
import sys

app = FastAPI()

@app.get("/api/v1/test")
def test():
    return {"status" : 200}

# @app.get("/data" ,response_model=list[KeywordOut])
# async def test():
#     data = await getKeywordAll()
#     return data

# @app.get("/one" ,response_model=KeywordOut)
# async def test():
#     data = await getKeywordById()
#     return data

@app.get("/api/v1/crawl")
async def testTwo(keyword: Union[str,None] = None , domain: Union[str,None] = None):
    if not keyword:
        keyword = "Travel Sri lanka"

    if not domain :
        domain = "com"
    result = await exec(keyword , domain)
    return result

@app.get("/test/{id}")
def read(id:int , q: Union[str,None] = None):
    return {"item_id" : id , "q" : q}


@app.post("/api/v1/test/crawl")
def crawl():
    urls = [
        "https://docs.celeryq.dev/en/v5.5.3/getting-started/introduction.html",
        "https://www.customs.gov.lk/"
    ]
    keywordId = "68f48913724b157215062943"

    # --- Determine the correct Python path ---
    python_path = os.path.join(sys.prefix, "Scripts", "python.exe") 
    
    if not os.path.exists(python_path):
        python_path = os.path.join(sys.prefix, "bin", "python")

    # --- Use an absolute path to your runner script ---
    base_dir = os.path.dirname(os.path.abspath(__file__))
    runner_script_path = os.path.join(base_dir, "web_crawl_runner.py")

    # 🔍 Build command
    command = [python_path, runner_script_path] + urls + [keywordId]
    
    print("=" * 80)
    print("🚀 Executing command:")
    print(f"   Python: {python_path}")
    print(f"   Script: {runner_script_path}")
    print(f"   URLs ({len(urls)}):")
    for i, url in enumerate(urls, 1):
        print(f"      [{i}] {url}")
    print(f"   Keyword ID: {keywordId}")
    print(f"\n   Full command: {' '.join(command)}")
    print("=" * 80)

    # ✅ Run Scrapy script in a separate process
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=base_dir,
            timeout=300  # 5 minute timeout
        )

        print("\n📤 STDOUT:")
        print(process.stdout)
        
        if process.stderr:
            print("\n⚠️ STDERR:")
            print(process.stderr)
        
        print(f"\n🏁 Return code: {process.returncode}")

        return {
            "status": "success" if process.returncode == 0 else "error",
            "message": "Crawling completed" if process.returncode == 0 else "Crawling failed",
            "urls_sent": urls,
            "urls_count": len(urls),
            "keyword_id": keywordId,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "return_code": process.returncode
        }
        
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Crawling timed out after 5 minutes",
            "urls_sent": urls,
            "keyword_id": keywordId
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to run crawler: {str(e)}",
            "urls_sent": urls,
            "keyword_id": keywordId
        }