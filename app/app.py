import os
import re
import requests
from dotenv import load_dotenv
from xai_sdk import Client
from xai_sdk.chat import system, user, file
from playwright.sync_api import sync_playwright


load_dotenv()

client = Client(api_key=os.getenv("XAI_API_KEY"))
chat = client.chat.create(model="grok-4")

def ask_file(prompt:str):
    agent_file_id = "file_6ed62445-f5fe-4478-a588-e7fc3c8a796c"
    
    chat.append(system("You are an information agent. Your job is to pick the closest integration section from the document we're looking at and provide the exact name, description and the list of URLs the integration has if it has any."))
    chat.append(user(prompt, file(agent_file_id)))
    print("🔎 Agent is searching for answer...")
    response = chat.sample()
    print("ANSWER:\n")
    return response.content

def extract_urls_from_content(content):
    # given the content, grab the URLs and put it into a python list
    js_urls_in_content = re.findall(r'https?://[^\s"\'<>]+\.js', content)
    return js_urls_in_content

def check_script_on_website(website_url, script_to_find):
    # Check if a script URL loads on a website and show its initiator.

    all_responses = []

    with sync_playwright() as p:
        # Launch headless browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Collect ALL requests into a list
        page.on("response", lambda res: all_responses.append(res))

        # Visit the website
        print(f"Checking {website_url}...")
        page.goto(website_url, wait_until="networkidle")
        browser.close()
    
    # print(f"ALL NETWORK REQUESTS: {all_responses}")

    # Now filter the requests to find matching scripts
    found_scripts = []
    for response in all_responses:
        if script_to_find in response.url:
            found_scripts.append(
                {
                    "script_url": response.url,
                    "script_status": response.status,
                    "initiator": response.frame.url if response.frame else "Unknown"
                }
            )
    for script in found_scripts:
        print(f"Script URL: {script["script_url"]}")
        print(f"Script Status: {script["script_status"]}")
        print(f"Script Initiator: {script["initiator"]}")
    return found_scripts

            


if __name__ == "__main__":
    content = ask_file("What does the srp integration do?")
    integration_urls = extract_urls_from_content(content)
    results = check_script_on_website(website_url="https://gooba.motivehq.site/", script_to_find=integration_urls[0])
    print(results)
