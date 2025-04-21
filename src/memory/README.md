# Memory MCP Server

A Model Context Protocol (MCP) implementation that enables AI assistants to save conversation memories to Google Docs.

## Overview

This server implements the Model Context Protocol (MCP) to provide AI assistants with memory capabilities. When integrated with compatible language models, it allows them to save important information from conversations, creating a persistent memory system stored in Google Docs.

## Features

- `remember_this` tool: Allows the AI to store conversation summaries in a Google Doc
- Automatic timestamp generation for each memory entry
- Secure authentication with Google Docs API

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

## License

[Specify your license here] 