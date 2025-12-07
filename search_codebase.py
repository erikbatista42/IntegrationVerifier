import os
import requests
import json
from rich.markdown import Markdown
from rich.console import Console

from dotenv import load_dotenv
load_dotenv()

from xai_sdk import Client
from xai_sdk.chat import user, system, file

client = Client(api_key=os.getenv("XAI_API_KEY"), timeout=3600)
xai_api_key = os.getenv("XAI_API_KEY")
greptile_api_key = os.getenv("GREPTILE_API_KEY")

def index_repo(repo="erikbatista42/tiny-llm"):
    """Index a repo with Greptile (run once before querying)"""
    response = requests.post(
        "https://api.greptile.com/v2/repositories",
        headers={
            "Authorization": f"Bearer {greptile_api_key}",
            "Content-Type": "application/json"
        },
        json={
            "remote": "github",
            "repository": repo,
            "branch": "main"
        }
    )
    print("Index response:", response.status_code, response.json())
    return response.json()

# Run this FIRST (comment out after it succeeds)
# index_repo()

def ask_about_code(question, repo="erikbatista42/tiny-llm"):
    """Query codebase and get answer from Greptile"""
    response = requests.post(
        "https://api.greptile.com/v2/query",
        headers={
            "Authorization": f"Bearer {greptile_api_key}",
            "Content-Type": "application/json"
        },
        json={
            "messages": [{"role": "user", "content": question}],
            "repositories": [{"remote": "github", "repository": repo, "branch": "main"}]
        }
    )
    result = response.json()
    return result.get("message", "No answer found.")

def extract_urls_with_grok(text: str) -> list[dict]:
    """
    Use Grok to extract relevant URLs from text.
    Returns a list of dicts with 'url' and 'description' keys.
    """
    chat = client.chat.create(
        model="grok-4-1-fast",  # Fast and cheap for extraction tasks
    )
    
    chat.append(system("""
You are a URL extractor. Given text, extract all URLs that appear to be:
- Script URLs (.js files)
- API endpoints
- Asset URLs (images, CSS, etc.)
- Any other relevant resource URLs

Return a JSON object with this exact structure:
{
    "urls": [
        {
            "url": "https://example.com/script.js",
            "type": "script",
            "description": "Brief description of what this URL is for"
        }
    ]
}

If no URLs are found, return: {"urls": []}
Only include complete, valid URLs (starting with http:// or https://).
"""))
    
    chat.append(user(f"Extract all relevant URLs from this text:\n\n{text}"))
    
    response = chat.sample()
    
    try:
        result = json.loads(response.content)
        return result.get("urls", [])
    except json.JSONDecodeError:
        print("⚠️ Failed to parse Grok response as JSON")
        return []

console = Console()

# Only run this when executing the file directly, NOT when importing
if __name__ == "__main__":
    answer = ask_about_code("Tell me how the srp is integrated")

    # console.print(Markdown(answer))
    result = extract_urls_with_grok(answer)
    urls = []
    for item in result:
        urls.append(item['url'])

    print(urls)

