import gradio as gr
from search_codebase import ask_about_code, extract_urls_with_grok
from script_locator import check_multiple_files, format_call_stack

    
def chat(message, history, website_url):
    """Handle user message and return response."""
    # 1. Ask Greptile about the codebase
    answer = ask_about_code(message)
    
    # 2. Extract URLs from the answer
    url_data = extract_urls_with_grok(answer)
    urls = [item['url'] for item in url_data]
    
    # 3. Build response
    response = f"**Answer:**\n{answer}\n\n"
    
    # 4. Check URLs if any were found
    if urls and website_url.strip():
        response += f"**Found {len(urls)} URL(s). Checking on {website_url}...**\n\n"
        results = check_multiple_files(website_url.strip(), urls, headless=True)
        
        for url, result in results.items():
            if result["found"]:
                response += f"✅ **FOUND** `{url}`\n"
                response += f"   Matched {len(result['matching_requests'])} request(s)\n\n"
                
                for rid, data in result["matching_requests"].items():
                    response += f"   📄 **URL:** `{data['url']}`\n"
                    response += f"   **Method:** {data['method']}\n"
                    
                    if data["status"]:
                        status_emoji = "✅" if 200 <= data["status"] < 400 else "⚠️"
                        response += f"   **Status:** {status_emoji} {data['status']} {data['status_text']}\n"
                    
                    if data["error"]:
                        response += f"   ❌ **Error:** {data['error']}\n"
                    if data["blocked_reason"]:
                        response += f"   🚫 **Blocked:** {data['blocked_reason']}\n"
                    
                    response += f"   📍 **Initiator Type:** {data['initiator_type']}\n"
                    if data["initiator_url"]:
                        response += f"   📍 **Initiator URL:** `{data['initiator_url']}`\n"
                    
                    response += f"\n   📚 **Call Stack:**\n```\n{format_call_stack(data['initiator_stack'])}\n```\n\n"
            else:
                response += f"❌ **NOT FOUND** `{url}`\n"
                response += "   💡 Possible reasons:\n"
                response += "   - The script URL might be different\n"
                response += "   - The script might be conditionally loaded\n"
                response += "   - The script might load on a different page\n\n"
                
    elif urls:
        response += f"**Found {len(urls)} URL(s) but no website URL provided to check.**\n"
        for url in urls:
            response += f"• `{url}`\n"
    
    return response 

# Launch the chat UI
demo = gr.ChatInterface(
    fn=chat,
    title="IntegrationVerifier",
    description="AI-powered tool to verify script integrations. Ask questions about your codebase and check if scripts are loading on live websites.",
    additional_inputs=[
        gr.Textbox(
            label="Website URL to Check",
            placeholder="https://example.com/",
            value="https://gooba.motivehq.site/",
            info="Enter the website URL where scripts should be verified"
        )
    ],
    theme="soft"
)

if __name__ == "__main__":
    demo.launch()
