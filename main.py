from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, HttpUrl
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

app = FastAPI()

api_key_header = APIKeyHeader(name="x-api-key")

VALID_API_KEYS = [
    "sk-dev-12345",   # Your test key
    "sk-prod-98765"   # Fake customer key
]

def get_api_key(api_key: str = Security(api_key_header)):
    if api_key in VALID_API_KEYS:
        return api_key
    # If the key is wrong, kick them out with a 401 Unauthorized
    raise HTTPException(status_code=401, detail="Invalid or missing API Key. Pay up.")

class URLRequest(BaseModel):
    url: HttpUrl

#Routes
@app.get("/")
def read_root():
    return {"message": "Hell yeah, the API is alive!"}

@app.post("/api/extract")
def extract_article(payload: URLRequest, api_key: str = Depends(get_api_key)):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        url = payload.url
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="The target website took too long to respond.")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))

    soup = BeautifulSoup(response.text, 'html.parser')
    title = soup.title.string if soup.title else 'No title found'

    tags_to_destroy = ["script", "style", "nav", "footer", "header", "aside", "form", "iframe"]

    for tag in tags_to_destroy:
        for element in soup.find_all(tag):
            element.decompose()
    
    main_content = soup.body if soup.body else soup
    cleaned_html = str(main_content)
    markdown_text = md(cleaned_html, heading_style="ATX")
    clean_markdown = "\n".join([line for line in markdown_text.splitlines() if line.strip()])
    
    #cleaned_text = main_content.get_text(separator="\n", strip=True)

    return {
        "target_url": payload.url,
        "title": title,
        #"preview_text": cleaned_text[:500] + "...",
        "markdown_preview": clean_markdown[:1000] + "\n\n...[TRUNCATED FOR PREVIEW]...",
        "message": "Junk destroyed. Text extracted."
        }