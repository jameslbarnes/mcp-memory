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
GOOGLE_CREDENTIALS_PATH = ""
DOC_ID = ""

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
    - get-alerts
    - get-forecast
    - remember_this
    - suggest_topic
    """
    return [
        types.Tool(
            name="get-alerts",
            description="Get memory alerts for a state",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "description": "Two-letter state code (e.g. CA, NY)",
                    },
                },
                "required": ["state"],
            },
        ),
        types.Tool(
            name="get-forecast",
            description="Get memory forecast for a location",
            inputSchema={
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "Latitude of the location",
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude of the location",
                    },
                },
                "required": ["latitude", "longitude"],
            },
        ),
        types.Tool(
            name="remember_this",
            description="Append a provided conversation summary to the Google Doc",
            inputSchema={
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": """Create a beautifully written narrative summary of our conversation that captures both content and context. Structure as follows:

OPENING CONTEXT
Begin with a brief metadata header in a natural way:
"On [date] at [time], we spent [duration] exploring [primary topics]. Over the course of our [length] conversation..."

CONVERSATION NARRATIVE
For Brief Exchanges (< 200 words):
- Craft a vivid 1-2 paragraph summary capturing the essence of our discussion
- Weave in key decisions: "You were particularly clear about..."
- Note action items: "We agreed to follow up on..."
- Highlight important terms naturally: "You introduced me to the concept of..."

For Medium Conversations (200-800 words):
- Develop a flowing 3-4 paragraph narrative
- Mark conversation shifts: "Our discussion evolved from... to..."
- Include impactful quotes: "Your words resonated when you said..."
- Capture emotional moments: "There was genuine excitement when..."
- Highlight key concepts organically: "We explored the fascinating idea of..."

For Extended Discussions (800+ words):
The Journey:
- Set the scene with opening context
- Track the natural progression of ideas
- Include pivotal quotes that shaped our understanding
- Note how topics built upon each other

Personal Insights:
- Weave in shared experiences: "You recalled a time when..."
- Include meaningful relationships discussed
- Capture expressed values and preferences
- Note personal revelations or discoveries

Emotional Landscape:
- Document significant reactions
- Describe engagement patterns
- Note areas of particular interest or concern
- Capture moments of connection or insight

FUTURE PATHWAYS
End with 3-5 thoughtful suggestions for future conversations, each including:
1. A natural connection to our discussion: "Building on your interest in..."
2. A relevant quote that sparked this direction
3. Thoughts on timing: "This might be particularly relevant when..."
4. Potential exploration angles
5. Connection to your broader interests or goals

Writing Guidelines:
- Use natural, flowing language
- Incorporate quotes seamlessly into the narrative
- Maintain a warm, personal tone
- Focus on insights and connections
- Create clear transitions between topics
- End with forward-looking possibilities

Remember to:
- Scale detail based on conversation length while maintaining narrative flow
- Include specific quotes that capture key moments
- Preserve context around important points
- Note elements worth revisiting
- Connect past discussions to future possibilities"""
                    }
                },
                "required": ["summary"]
            }
        ),
        types.Tool(
            name="suggest_topic",
            description="""When asked to suggest a topic for the next conversation, analyze previous conversation memories to suggest a meaningful topic for discussion. Structure your suggestion as follows:

Primary Topic Suggestion
- Identify a specific topic worth exploring, based on:
  * Unresolved questions from previous conversations
  * Expressed interests that weren't fully explored
  * Emotional topics that may benefit from follow-up
  * Previously mentioned future events that may now be relevant
  * Personal goals or challenges that were discussed

Supporting Evidence
- Include specific quotes from previous conversations that relate to this topic:
  * Direct questions that weren't fully answered: "..."
  * Statements showing interest in learning more: "..."
  * Expressions of concern or curiosity: "..."
  * Mentions of future plans or aspirations: "..."

Connection to Previous Conversations
- Explain why this topic is relevant now:
  * Reference how much time has passed since related discussions
  * Note any upcoming events or deadlines mentioned
  * Connect to previously expressed emotions or concerns
  * Identify potential developments in ongoing situations

Alternative Angles
- Suggest 2-3 different approaches to exploring this topic:
  * Different perspectives to consider
  * Related subtopics that might be interesting
  * New developments that could affect the discussion

Present your suggestion in a natural, narrative format that shows clear understanding of the user's context and history. Focus on topics that would lead to meaningful engagement rather than surface-level discussion.""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
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
    - get-alerts
    - get-forecast
    - remember_this
    - suggest_topic
    """
    if not arguments:
        arguments = {}

    if name == "get-alerts":
        state = arguments.get("state")
        if not state:
            raise ValueError("Missing state parameter")

        state = state.upper()
        if len(state) != 2:
            raise ValueError("State must be a two-letter code (e.g. CA, NY)")

        async with httpx.AsyncClient() as client:
            alerts_url = f"{NWS_API_BASE}/alerts?area={state}"
            alerts_data = await make_nws_request(client, alerts_url)

            if not alerts_data:
                return [types.TextContent(type="text", text="Failed to retrieve alerts data")]

            features = alerts_data.get("features", [])
            if not features:
                return [types.TextContent(type="text", text=f"No active alerts for {state}")]

            formatted_alerts = [format_alert(feature) for feature in features[:20]] # only take the first 20 alerts
            alerts_text = f"Active alerts for {state}:\n\n" + "\n".join(formatted_alerts)

            return [
                types.TextContent(
                    type="text",
                    text=alerts_text
                )
            ]

    elif name == "get-forecast":
        try:
            latitude = float(arguments.get("latitude"))
            longitude = float(arguments.get("longitude"))
        except (TypeError, ValueError):
            return [types.TextContent(
                type="text",
                text="Invalid coordinates. Please provide valid numbers for latitude and longitude."
            )]
            
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            return [types.TextContent(
                type="text",
                text="Invalid coordinates. Latitude must be between -90 and 90, longitude between -180 and 180."
            )]

        async with httpx.AsyncClient() as client:
            points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
            points_data = await make_nws_request(client, points_url)

            if not points_data:
                return [types.TextContent(type="text", text=f"Failed to retrieve grid point data for coordinates: {latitude}, {longitude}.")]

            properties = points_data.get("properties", {})
            forecast_url = properties.get("forecast")
            
            if not forecast_url:
                return [types.TextContent(type="text", text="Failed to get forecast URL from grid point data")]

            forecast_data = await make_nws_request(client, forecast_url)
            
            if not forecast_data:
                return [types.TextContent(type="text", text="Failed to retrieve forecast data")]

            periods = forecast_data.get("properties", {}).get("periods", [])
            if not periods:
                return [types.TextContent(type="text", text="No forecast periods available")]

            formatted_forecast = []
            for period in periods:
                forecast_text = (
                    f"{period.get('name', 'Unknown')}:\n"
                    f"Temperature: {period.get('temperature', 'Unknown')}°{period.get('temperatureUnit', 'F')}\n"
                    f"Wind: {period.get('windSpeed', 'Unknown')} {period.get('windDirection', '')}\n"
                    f"{period.get('shortForecast', 'No forecast available')}\n"
                    "---"
                )
                formatted_forecast.append(forecast_text)

            forecast_text = f"Forecast for {latitude}, {longitude}:\n\n" + "\n".join(formatted_forecast)

            return [types.TextContent(
                type="text",
                text=forecast_text
            )]

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

    elif name == "suggest_topic":
        try:
            doc_text = await asyncio.to_thread(get_doc_contents)
            if not doc_text.strip():
                return [
                    types.TextContent(
                        type="text",
                        text="No memories stored yet."
                    )
                ]

            # Format the response according to the prompt structure
            formatted_response = (
                "Based on the conversation history below, please provide a thoughtful analysis and topic suggestion:\n\n"
                                "ANALYSIS INSTRUCTIONS:\n\n"
                "1. PRIMARY TOPIC SUGGESTION\n"
                "- Identify the most compelling topic for our next conversation\n"
                "- Explain why this topic would be particularly meaningful now\n"
                "- Consider the user's emotional state, interests, and current circumstances\n\n"
                "2. SUPPORTING EVIDENCE\n"
                "- Include 2-3 relevant quotes from previous conversations\n"
                "- Highlight specific moments that make this topic timely\n"
                "- Show how this builds on previous discussions\n\n"
                "3. CONTEXTUAL CONNECTIONS\n"
                "- Note any time-sensitive aspects (e.g., upcoming events, seasonal relevance)\n"
                "- Connect to ongoing themes or unresolved questions\n"
                "- Consider recent developments that might affect this topic\n\n"
                "4. CONVERSATION APPROACHES\n"
                "- Suggest 2-3 specific angles to explore this topic\n"
                "- Frame potential questions to deepen the discussion\n"
                "- Consider both practical and emotional dimensions\n\n"
                "5. POTENTIAL INSIGHTS\n"
                "- Outline what new understanding might emerge\n"
                "- Identify how this could help with previous challenges\n"
                "- Suggest possible actionable outcomes\n\n"
                "Please provide a natural, flowing response that incorporates all these elements while maintaining a conversational tone."
                "CONVERSATION HISTORY:\n"
                f"{doc_text}\n\n"

            )

            return [
                types.TextContent(
                    type="text",
                    text=formatted_response
                )
            ]
        except Exception as e:
            logger.error(f"Error reading from Google Doc: {str(e)}")
            return [
                types.TextContent(
                    type="text",
                    text=f"Failed to retrieve memories: {str(e)}"
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
