# 🕷️ AI-Powered Web Crawler with Knowledge Graph Generation

An advanced web crawling system that automatically extracts content from websites, generates knowledge graphs using AI (Google Gemini), and stores them in Neo4j for intelligent querying and decision-making.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.119-green)
![LangChain](https://img.shields.io/badge/LangChain-1.0-orange)
![Neo4j](https://img.shields.io/badge/Neo4j-5.22-blue)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-green)

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [API Endpoints](#-api-endpoints)
- [How It Works](#-how-it-works)
- [Project Structure](#-project-structure)
- [Usage Examples](#-usage-examples)

## ✨ Features

- **🌐 Intelligent Web Crawling**: Scrapy-based crawler with smart link following and social media extraction
- **🤖 AI-Powered Knowledge Graph Generation**: Uses Google Gemini 2.5 Flash to extract entities and relationships
- **📊 Neo4j Graph Database**: Stores knowledge graphs for complex relationship queries
- **🔄 Automatic Content Chunking**: Handles large content by splitting into manageable chunks
- **💾 MongoDB Storage**: Stores crawled content, keywords, and summaries
- **🧠 AI Reasoning Agent**: Query the knowledge graph using natural language
- **📝 Auto-Summarization**: Generates AI summaries of crawled content
- **🔗 Incremental KG Updates**: MERGE mode adds to existing graphs without losing data

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER REQUEST                                    │
│                        (keyword, optional URLs)                              │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FASTAPI BACKEND                                    │
│                              main.py                                         │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  ↓
        ┌─────────────────────────┼─────────────────────────┐
        ↓                         ↓                         ↓
┌───────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   MONGODB     │       │  WEB CRAWLER    │       │   NEO4J         │
│               │       │  (Scrapy)       │       │  Knowledge      │
│ • Keywords    │       │                 │       │  Graph          │
│ • Site Data   │       │ • Extract text  │       │                 │
│ • Summaries   │       │ • Follow links  │       │ • Nodes         │
└───────────────┘       │ • Get images    │       │ • Relationships │
                        └────────┬────────┘       └────────┬────────┘
                                 ↓                         ↑
                        ┌─────────────────┐                │
                        │  LANGGRAPH      │                │
                        │  AI AGENTS      │────────────────┘
                        │                 │
                        │ • getCrawlContent
                        │ • createKG      │
                        │ • queryNeo4J    │
                        └────────┬────────┘
                                 ↓
                        ┌─────────────────┐
                        │  GOOGLE GEMINI  │
                        │  2.5 Flash LLM  │
                        │                 │
                        │ • Entity Extract│
                        │ • KG Generation │
                        │ • Summarization │
                        └─────────────────┘
```

## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| **Backend Framework** | FastAPI |
| **Web Crawling** | Scrapy |
| **AI/LLM** | Google Gemini 2.5 Flash |
| **Agent Framework** | LangChain + LangGraph |
| **Graph Database** | Neo4j |
| **Document Database** | MongoDB Atlas |
| **HTML Parsing** | BeautifulSoup4 |
| **Async Support** | Motor (MongoDB), asyncio |

## 📦 Installation

### Prerequisites

- Python 3.13+
- MongoDB Atlas account
- Neo4j Aura account (or local Neo4j)
- Google AI API key

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/dinethjanitha/webcrawl.git
cd webcrawl
```

2. **Create virtual environment**
```bash
python -m venv .
# Windows
Scripts\activate
# Linux/Mac
source bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
Create a `.env` file in the root directory:
```env
CONNECTION_STRING=mongodb+srv://your-username:your-password@cluster.mongodb.net/
GOOGLE_API_KEY=your-google-ai-api-key
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-neo4j-password
```

5. **Run the application**
```bash
fastapi dev main.py
```

The API will be available at `http://localhost:8000`

## ⚙️ Configuration

### Chunking Settings (crawlProcess.py)
```python
MAX_CHUNK_SIZE = 5000   # Characters per chunk
CHUNK_OVERLAP = 500     # Overlap between chunks
```

### Crawler Settings (web_spider_new.py)
```python
custom_settings = {
    'ROBOTSTXT_OBEY': False,
    'CONCURRENT_REQUESTS': 1,
    'DOWNLOAD_DELAY': 1,
    'DOWNLOAD_TIMEOUT': 30,
    'CLOSESPIDER_PAGECOUNT': 3,  # Max pages per crawl
}
```

## 🔌 API Endpoints

### Crawl a Website
```http
POST /api/v1/crawl?keyword={url}&url_list={additional_urls}
```
Crawls the specified URL(s), generates knowledge graph, and creates summary.

**Parameters:**
- `keyword` (string): Main URL/domain to crawl
- `url_list` (array): Additional URLs to include

**Response:**
```json
{
  "status": "success",
  "keyword_id": "507f1f77bcf86cd799439011",
  "urls_crawled": 5,
  "urls": ["https://example.com", ...],
  "summary": "## Summary\n..."
}
```

### Query Knowledge Graph
```http
GET /api/v1/dicission?keywordId={id}&user_prompt={question}
```
Ask questions about the crawled data using natural language.

**Parameters:**
- `keywordId` (string): MongoDB ObjectId of the keyword
- `user_prompt` (string): Your question in natural language

**Response:**
```json
{
  "status": "success",
  "message": "Based on the knowledge graph analysis..."
}
```

### Get Full Details
```http
GET /api/v1/keyword/full?keyword={id}
```
Returns all crawled data, content, and summary for a keyword.

### Get All Keywords
```http
GET /api/v1/keyword/all
```
Returns list of all previously crawled keywords.

### Delete Crawl Data
```http
DELETE /api/v1/keyword/{id}
```
Deletes all data associated with a keyword ID.

### Health Check
```http
GET /api/v1/test
```
Returns `{"status": 200}` if API is running.

## 🔄 How It Works

### Complete Workflow

```
1. User Request (keyword + optional URLs)
        ↓
2. Store/Check Keyword in MongoDB
        ↓
3. Web Crawl (Scrapy subprocess)
   • Extract text content
   • Collect images
   • Find social media links
   • Store in MongoDB (sitesData)
        ↓
4. AI Agent Processing (LangGraph)
   ├─→ getCrawlContent(): Fetch from MongoDB
   │   └─→ If content > 5000 chars: CHUNK
   │       ├─→ Split into overlapping chunks
   │       ├─→ Process each chunk with LLM
   │       ├─→ Merge partial KGs
   │       └─→ Save to Neo4j
   │
   └─→ createKG(): Generate Knowledge Graph
       └─→ If small content: Direct LLM processing
           └─→ Save to Neo4j
        ↓
5. Generate AI Summary
        ↓
6. Return Results to User
```

### Knowledge Graph Structure

**Nodes:**
```json
{
  "label": "Company",
  "name": "SLT Mobitel",
  "properties": {
    "type": "Telecommunications",
    "country": "Sri Lanka"
  }
}
```

**Edges:**
```json
{
  "from": "SLT Mobitel",
  "type": "PROVIDES",
  "to": "Fiber Internet",
  "properties": {}
}
```

## 📁 Project Structure

```
webcrawl/
├── main.py                    # FastAPI application & endpoints
├── crawlProcess.py            # Core processing logic & AI agents
├── web_crawl_runner.py        # Scrapy subprocess runner
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables
│
├── connection/
│   ├── database.py            # MongoDB connection
│   └── mongocon.py            # MongoDB utilities
│
├── model/
│   ├── keyword.py             # Keyword collection
│   ├── siteData.py            # Site data collection
│   └── summary.py             # Summary collection
│
├── schema/
│   ├── keywordSchema.py       # Pydantic models for keywords
│   ├── fullDetailsSchema.py   # Full response schema
│   ├── sitesDataSchema.py     # Site data schema
│   └── summarySchema.py       # Summary schema
│
├── service/
│   └── privousChats.py        # Data retrieval services
│
├── config/
│   ├── objectIdConterver.py   # ObjectId converter
│   └── get_schema.py          # Schema utilities
│
├── webscrapy/
│   └── webscrapy/
│       └── spiders/
│           ├── web_spider.py      # Basic spider
│           └── web_spider_new.py  # Advanced spider with link following
│
└── googlesearchmethod/
    └── googlesearch.py        # Google search integration
```

## 💡 Usage Examples

### 1. Crawl a Company Website
```bash
curl -X POST "http://localhost:8000/api/v1/crawl?keyword=https://www.slt.lk" \
  -H "Content-Type: application/json" \
  -d '[]'
```

### 2. Crawl with Additional URLs
```bash
curl -X POST "http://localhost:8000/api/v1/crawl?keyword=https://example.com" \
  -H "Content-Type: application/json" \
  -d '["https://example.com/about", "https://example.com/products"]'
```

### 3. Query the Knowledge Graph
```bash
curl "http://localhost:8000/api/v1/dicission?keywordId=507f1f77bcf86cd799439011&user_prompt=What%20services%20does%20this%20company%20offer?"
```

### 4. Get Crawl Summary
```bash
curl "http://localhost:8000/api/v1/keyword/full?keyword=507f1f77bcf86cd799439011"
```

## 🐳 Docker Support

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0"]
```

Build and run:
```bash
docker build -t webcrawl .
docker run -p 8000:8000 --env-file .env webcrawl
```

## 🔒 Security Notes

- Never commit `.env` file to version control
- Use environment variables for all sensitive data
- The crawler respects `ROBOTSTXT_OBEY` setting (currently disabled for flexibility)
- Rate limiting is built-in via `DOWNLOAD_DELAY`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 👨‍💻 Author

**Dineth Janitha**
- GitHub: [@dinethjanitha](https://github.com/dinethjanitha)

---

⭐ Star this repo if you find it useful!
