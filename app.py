import gradio as gr
from search_codebase import ask_about_code, extract_urls_with_grok
from script_locator import check_multiple_files

def chat(message, history):
    """Handle user message and return response."""
    # 1. Ask Greptile about the codebase
    answer = ask_about_code(message)
    
    # 2. Extract URLs from the answer
    url_data = extract_urls_with_grok(answer)
    urls = [item['url'] for item in url_data]
    
    # 3. Build response
    response = f"**Answer:**\n{answer}\n\n"
    
    # 4. Check URLs if any were found
    if urls:
        response += f"**Found {len(urls)} URL(s). Checking on website...**\n\n"
        website_url = "https://gooba.motivehq.site/"
        results = check_multiple_files(website_url, urls, headless=True)
        
        for url, result in results.items():
            status = "✅ FOUND" if result["found"] else "❌ NOT FOUND"
            response += f"{status}: `{url}`\n"
    
    return response

# Launch the chat UI
demo = gr.ChatInterface(
    fn=chat,
    title="🔍 Codebase Support Agent",
    description="Ask questions about the codebase. I'll search the code and verify any URLs on the live site.",
    examples=[
        "How does the SRP integrate?",
        "Where is the Gubagoo script loaded?",
        "What API endpoints are used?"
    ],
    theme="soft"
)

if __name__ == "__main__":
    demo.launch()