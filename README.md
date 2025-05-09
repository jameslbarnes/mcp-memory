# mcp-memory
# Memory MCP Server

A Model Context Protocol (MCP) implementation that enables AI assistants to save conversation memories to Google Docs.

## Overview

This server implements the Model Context Protocol (MCP) to provide AI assistants with memory capabilities. When integrated with compatible language models, it allows them to save important information from conversations, creating a persistent memory system stored in Google Docs.

## Features

- `remember_this` tool: Allows the AI to store conversation summaries in a Google Doc
- Automatic timestamp generation for each memory entry
- Secure authentication with Google Docs API
- Cross-platform memory sharing between different AI assistants

## Requirements

- Python 3.8+
- Google Cloud Service Account with Google Docs API access
- Required Python packages:
  - httpx
  - python-dotenv
  - google-auth
  - google-api-python-client
  - mcp (Model Context Protocol)
- Environment variables:
  - `GOOGLE_CREDENTIALS_PATH`: Path to the service account credentials file
  - `DOCUMENT_ID`: The ID of the Google Doc to use as memory storage

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt` (create this file with the dependencies listed above)
3. Set up environment variables (see below)

## Environment Setup

Create a `.env` file with the following:

```
GOOGLE_CREDENTIALS_PATH=path/to/your/credentials.json
DOCUMENT_ID=your_google_doc_id
```

## Usage

### Run as a standalone server

```
python server.py
```

### Import as a package

```python
from memory import main

if __name__ == "__main__":
    main()
```

The server communicates via stdin/stdout using the MCP protocol.

## Integration with AI Models

This server is designed to be used with AI models that support the Model Context Protocol. When properly integrated, the AI can use the `remember_this` tool to save important information from conversations.

## Transferring Memories Across AI Platforms

You can use the same Google Doc as a memory repository across different AI assistants to maintain context continuity. Here's how to attach the same Google Doc to different platforms:

### ChatGPT

1. Create a new chat or open an existing one on [chat.openai.com](https://chat.openai.com)
2. Access GPT settings and enable the "Web Browsing" plugin
3. Share your Google Doc with the appropriate permissions (public or specific access)
4. Provide the Google Doc URL to ChatGPT in your conversation
5. Ask ChatGPT to reference the document for context in future interactions

### Claude

1. Start a new conversation in Claude or continue an existing thread
2. Upload your Google Doc directly to the conversation using the attachment feature
3. Alternatively, share the Google Doc link with Claude
4. Ask Claude to review the document for context
5. For Claude projects (Anthropic's persistent workspace feature), attach the document to the project for continuous access

### Gemini

1. Open Gemini chat at [gemini.google.com](https://gemini.google.com)
2. Use the Google account that has access to your memory Google Doc
3. Reference the document directly since Gemini has native integration with Google Docs
4. You can ask Gemini to "use the document [document name] for context"
5. For new conversations, explicitly ask Gemini to reference the same document

### Tips for Cross-Platform Memory Sharing

- Use a consistent format in your Google Doc for easy parsing by different AI models
- Include clear section headers and timestamps
- When switching platforms, explicitly instruct the AI to reference the shared memory document
- Consider creating a table of contents or index at the top of the document
- Update the `DOCUMENT_ID` environment variable to point to the same Google Doc across all instances

## MCP Protocol Implementation

The server implements the following MCP endpoints:
- `list_tools`: Returns available tools (`remember_this`)
- `call_tool`: Executes the requested tool function with the provided arguments

The Model Context Protocol enables:
- Standardized communication between language models and external tools
- Tool discovery through the `list_tools` endpoint
- Tool execution through the `call_tool` endpoint
- Structured input/output through JSON schema validation

The server uses the MCP stdio communication method for transmitting requests and responses.