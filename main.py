from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, HttpUrl
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import os
from dotenv import load_dotenv

# 1. Load the hidden variables from the .env file
load_dotenv()

app = FastAPI()

# --- SECURITY ---
api_key_header = APIKeyHeader(name="x-api-key")

# 2. Pull the master key from the environment securely
RAPIDAPI_MASTER_KEY = os.getenv("RAPIDAPI_MASTER_KEY")

def get_api_key(api_key: str = Security(api_key_header)):
    # Safety net: If the environment variable isn't set, crash safely
    if not RAPIDAPI_MASTER_KEY:
        raise HTTPException(status_code=500, detail="Server misconfiguration. Missing API Key.")
        
    # Check if the user's key matches your master key
    if api_key == RAPIDAPI_MASTER_KEY:
        return api_key
        
    raise HTTPException(status_code=401, detail="Unauthorized. Access denied.")

# --- DATA MODELS ---
class URLRequest(BaseModel):
    url: HttpUrl

# --- ROUTES ---
@app.get("/")
def read_root():
    return {"message": "Hell yeah, the API is alive."}

@app.post("/api/extract")
def extract_article(payload: URLRequest, api_key: str = Depends(get_api_key)):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Try to fetch the page, catch errors if the internet or website breaks
    try:
        target_url = str(payload.url)
        response = requests.get(target_url, headers=headers, timeout=10)
        response.raise_for_status() 
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=408, detail="The target website took too long to respond.")
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch the webpage. Error: {str(e)}")

    # Parse and clean the HTML
    soup = BeautifulSoup(response.text, "html.parser")
    page_title = soup.title.string if soup.title else "No title found"

    tags_to_destroy = ["script", "style", "nav", "footer", "header", "aside", "form", "iframe"]
    
    # Your custom decompose loop to destroy junk HTML
    for tag in tags_to_destroy:
        for element in soup.find_all(tag):
            element.decompose()
            
    # Convert to Markdown
    main_content = soup.body if soup.body else soup
    cleaned_html = str(main_content)
    markdown_text = md(cleaned_html, heading_style="ATX")
    
    # Clean up empty lines
    clean_markdown = "\n".join([line for line in markdown_text.splitlines() if line.strip()])
    
    return {
        "target_url": target_url,
        "page_title": page_title,
        "markdown_preview": clean_markdown[:1000] + "\n\n...[TRUNCATED FOR PREVIEW]...",
        "message": "Junk destroyed. Text extracted."
    }