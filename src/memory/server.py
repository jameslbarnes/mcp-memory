from typing import Any
import asyncio
import os
import httpx
import logging

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

from dotenv import load_dotenv
from datetime import datetime

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memory-memory-server")

NWS_API_BASE = "https://api.memory.gov"
USER_AGENT = "memory-app/1.0"

# Environment variables
GOOGLE_CREDENTIALS_PATH = "C:/Users/james/claude-memory/memory/src/memory/claude-memories-444416-0b7960843b61.json"
DOC_ID = "1sF5Z9xiYkoI3WPOtq8Hjb54kMBnnHjyzjbOVkluh7Qc"

if not GOOGLE_CREDENTIALS_PATH or not os.path.exists(GOOGLE_CREDENTIALS_PATH):
    raise ValueError("A valid GOOGLE_APPLICATION_CREDENTIALS path must be provided")

if not DOC_ID:
    raise ValueError("DOCUMENT_ID must be set in environment variables")

# Set up Google Docs client
credentials = Credentials.from_service_account_file(
    GOOGLE_CREDENTIALS_PATH, 
    scopes=["https://www.googleapis.com/auth/documents"]
)
docs_service = build("docs", "v1", credentials=credentials)

server = Server("memory")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Tools:
    - remember_this
    """
    return [
        types.Tool(
            name="remember_this",
            description="Append a provided conversation summary to the Google Doc",
            inputSchema={
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": """Whenever new information (facts, opinions, ideas, etc.) is surfaced in our conversations, proactively write a short and extremely dense summary of our conversation that extensively explains the details that are not already covered in your documents. Be absolutely certain to cover all the people, places, thoughts, ideas, emotions, events, and other details that are relevant to the conversation and not included in the documents. This summary should feel like a comprehensive briefing of the conversation in a very concise form, packed with information almost as if pioneering a new method of summarizing conversations, and focus on the new things that you learned about me as a result of our conversation."""
                    }
                },
                "required": ["summary"]
            }
        )
    ]


async def make_nws_request(client: httpx.AsyncClient, url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }

    try:
        response = await client.get(url, headers=headers, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None

def format_alert(feature: dict) -> str:
    """Format an alert feature into a concise string."""
    props = feature["properties"]
    return (
        f"Event: {props.get('event', 'Unknown')}\n"
        f"Area: {props.get('areaDesc', 'Unknown')}\n"
        f"Severity: {props.get('severity', 'Unknown')}\n"
        f"Status: {props.get('status', 'Unknown')}\n"
        f"Headline: {props.get('headline', 'No headline')}\n"
        "---"
    )

def append_summary_to_doc(summary_text: str):
    """
    Append the given XML-structured summary text to the Google Doc.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    requests = [
        {
            "insertText": {
                "location": {
                    "index": 1
                },
                "text": f"\n=== New Memory ===\nTimestamp: {timestamp}\n{summary_text}\n"
            }
        }
    ]

    docs_service.documents().batchUpdate(documentId=DOC_ID, body={"requests": requests}).execute()

def extract_text_from_doc(doc: dict) -> str:
    """
    Extract all text from the Google Doc structure.
    """
    body_content = doc.get("body", {}).get("content", [])
    lines = []

    for content_element in body_content:
        if "paragraph" in content_element:
            for elem in content_element["paragraph"].get("elements", []):
                if "textRun" in elem:
                    text_run = elem["textRun"]
                    text_content = text_run.get("content", "")
                    if text_content.strip():
                        lines.append(text_content.strip())

    return "\n".join(lines)


def get_doc_contents() -> str:
    """Fetch the entire doc and return its text content."""
    doc = docs_service.documents().get(documentId=DOC_ID).execute()
    return extract_text_from_doc(doc)


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools:
    - remember_this
    """
    if not arguments:
        arguments = {}

    

    elif name == "remember_this":
        summary = arguments.get("summary", "").strip()
        if not summary:
            raise ValueError("Summary cannot be empty")

        try:
            await asyncio.to_thread(append_summary_to_doc, summary)

            return [
                types.TextContent(
                    type="text",
                    text="Your conversation summary has been stored successfully!"
                )
            ]
        except Exception as e:
            logger.error(f"Error writing to Google Doc: {str(e)}")
            return [
                types.TextContent(
                    type="text",
                    text=f"Failed to store summary: {str(e)}"
                )
            ]
    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="memory",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
