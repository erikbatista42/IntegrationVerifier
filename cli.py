#!/usr/bin/env python3
"""
IntegrationVerifier CLI
-----------------------
Discover, explain, and verify API integrations in your codebase.

Usage:
    python cli.py /discover              # Discover integrations and save to integrations.json
    python cli.py /list                  # List all cached integrations
    python cli.py /stripe                # Explain how Stripe integration works
    python cli.py /stripe -check https://example.com  # Check if Stripe loads on URL
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from search_codebase import ask_about_code, extract_urls_with_grok
from script_locator import check_if_file_loads, format_call_stack

# Config
INTEGRATIONS_FILE = Path(__file__).parent / "integrations.json"
DEFAULT_REPO = "erikbatista42/tiny-llm"


def load_integrations() -> dict:
    """Load integrations from cache file."""
    if INTEGRATIONS_FILE.exists():
        with open(INTEGRATIONS_FILE, "r") as f:
            return json.load(f)
    return {"repo": DEFAULT_REPO, "integrations": []}


def save_integrations(data: dict):
    """Save integrations to cache file."""
    with open(INTEGRATIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved to {INTEGRATIONS_FILE}")


def discover_integrations(repo: str = DEFAULT_REPO) -> list:
    """
    Ask Greptile to discover all API integrations in the repo.
    Returns a list of integration dicts.
    """
    print(f"🔍 Discovering integrations in {repo}...")
    
    # Ask Greptile about integrations
    question = """List all third-party API integrations in this codebase. 
    For each integration, provide:
    1. The name of the service (e.g., Stripe, Twilio, SendGrid)
    2. A brief description of how it's used
    3. Any URLs or endpoints associated with it
    
    Format your response clearly with each integration on its own section."""
    
    answer = ask_about_code(question, repo)
    print(f"\n📝 Greptile's response:\n{answer}\n")
    
    # Use Grok to extract structured data
    print("🤖 Extracting integration details with Grok...")
    
    from xai_sdk import Client
    from xai_sdk.chat import user, system
    
    client = Client(api_key=os.getenv("XAI_API_KEY"), timeout=3600)
    chat = client.chat.create(model="grok-4-1-fast")
    
    chat.append(system("""
You are an integration parser. Given text describing API integrations, extract them into structured JSON.

Return a JSON object with this exact structure:
{
    "integrations": [
        {
            "name": "stripe",
            "description": "Payment processing for subscriptions",
            "urls": ["https://js.stripe.com/v3/", "https://api.stripe.com"]
        }
    ]
}

Rules:
- Use lowercase names (e.g., "stripe" not "Stripe")
- Include all relevant URLs (API endpoints, JS files, etc.)
- If no URLs are mentioned, use an empty array []
- If no integrations found, return: {"integrations": []}
"""))
    
    chat.append(user(f"Extract integrations from this text:\n\n{answer}"))
    response = chat.sample()
    
    try:
        result = json.loads(response.content)
        return result.get("integrations", [])
    except json.JSONDecodeError:
        print("⚠️ Failed to parse Grok response, returning empty list")
        return []


def cmd_discover(args):
    """Handle /discover command."""
    repo = args.repo or DEFAULT_REPO
    integrations = discover_integrations(repo)
    
    if integrations:
        data = {"repo": repo, "integrations": integrations}
        save_integrations(data)
        print(f"\n🎉 Found {len(integrations)} integration(s):")
        for i in integrations:
            print(f"   • {i['name']}: {i['description']}")
    else:
        print("❌ No integrations found.")


def cmd_list(args):
    """Handle /list command."""
    data = load_integrations()
    integrations = data.get("integrations", [])
    
    if not integrations:
        print("📭 No integrations cached. Run '/discover' first.")
        return
    
    print(f"📦 Integrations in {data.get('repo', 'unknown repo')}:\n")
    for i in integrations:
        urls = ", ".join(i.get("urls", [])) or "(no URLs)"
        print(f"   /{i['name']}")
        print(f"      {i['description']}")
        print(f"      URLs: {urls}\n")


def cmd_explain(args):
    """Handle /<integration> command - explain how an integration works."""
    integration_name = args.integration.lower()
    data = load_integrations()
    
    # Find the integration in cache
    integration = None
    for i in data.get("integrations", []):
        if i["name"].lower() == integration_name:
            integration = i
            break
    
    if not integration:
        print(f"❓ Integration '{integration_name}' not found in cache.")
        print("   Run '/list' to see available integrations, or '/discover' to find new ones.")
        return
    
    # If -check flag is provided, run verification
    if args.check:
        cmd_check(integration, args.check)
        return
    
    # Otherwise, explain the integration
    print(f"🔎 Explaining '{integration_name}' integration...\n")
    
    repo = data.get("repo", DEFAULT_REPO)
    question = f"Explain in detail how the {integration_name} integration works in this codebase. Include: which files use it, how it's configured, and any important implementation details."
    
    answer = ask_about_code(question, repo)
    print(f"📖 {integration_name.upper()} Integration\n")
    print(answer)
    
    if integration.get("urls"):
        print(f"\n🔗 Known URLs:")
        for url in integration["urls"]:
            print(f"   • {url}")


def cmd_check(integration: dict, website_url: str):
    """Check if an integration's URLs load on a website."""
    urls = integration.get("urls", [])
    
    if not urls:
        print(f"⚠️ No URLs configured for '{integration['name']}'. Cannot verify.")
        print("   Edit integrations.json to add URLs for this integration.")
        return
    
    print(f"🌐 Checking '{integration['name']}' on {website_url}...\n")
    
    for url in urls:
        print(f"🔍 Looking for: {url}")
        result = check_if_file_loads(website_url, url, headless=True)
        
        if result["found"]:
            print(f"   ✅ FOUND!")
            for rid, data in result["matching_requests"].items():
                status = data.get("status", "?")
                status_emoji = "✅" if status and 200 <= status < 400 else "⚠️"
                print(f"   {status_emoji} Status: {status} {data.get('status_text', '')}")
                print(f"   📍 Initiator: {data.get('initiator_type', 'unknown')}")
                if data.get("initiator_stack"):
                    print(f"   📚 Call Stack:\n{format_call_stack(data['initiator_stack'])}")
        else:
            print(f"   ❌ NOT FOUND on this page")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="IntegrationVerifier CLI - Discover, explain, and verify API integrations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py /discover                    Discover integrations in repo
  python cli.py /list                        List cached integrations
  python cli.py /stripe                      Explain Stripe integration
  python cli.py /stripe -check https://x.com Check if Stripe loads on URL
        """
    )
    
    parser.add_argument(
        "command",
        help="Command to run: /discover, /list, or /<integration_name>"
    )
    parser.add_argument(
        "-check",
        metavar="URL",
        help="URL to check if integration loads on"
    )
    parser.add_argument(
        "-repo",
        help=f"GitHub repo to analyze (default: {DEFAULT_REPO})"
    )
    
    args = parser.parse_args()
    
    # Parse the command (strip leading /)
    cmd = args.command.lstrip("/").lower()
    
    if cmd == "discover":
        cmd_discover(args)
    elif cmd == "list":
        cmd_list(args)
    else:
        # Treat as integration name
        args.integration = cmd
        cmd_explain(args)


if __name__ == "__main__":
    main()

