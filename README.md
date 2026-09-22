# GitHub PR Review MCP Server

Name - Vidhatri Sudarshan Hegde
Netid - vh256@cornell.edu

A Python MCP server for the **Development Workflow** domain. It connects Claude
Desktop to GitHub for read-only pull request review.

## MCP Endpoints

| Endpoint | Type | Purpose |
| --- | --- | --- |
| `list_open_pull_requests` | Tool | Lists open pull requests in a repository. |
| `get_pull_request_details` | Tool | Gets metadata and changed-file patches for one pull request. |
| `review_pull_request` | Prompt | Gives Claude a structured code-review workflow. |

## Setup

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```sh
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env
```

Create a fine-grained GitHub personal access token with **Pull requests: Read-only**
permission. Add it to `.env`:

```dotenv
GITHUB_TOKEN=your_token_here
```

The `.env` file is excluded from Git.

## Run

```sh
source .venv/bin/activate
python server.py
```

The server uses the MCP `stdio` transport and is normally started automatically
by Claude Desktop.

## Claude Desktop Configuration

Copy the `mcpServers` entry from `claude_desktop_config.json` into:

```text
~/Library/Application Support/Claude/claude_desktop_config.json
```

Restart Claude Desktop, then try:

```text
Use pr-review-assistant to list open pull requests in vidhu-hegde/Fork-Fly.
```

## Security Practices

1. **Input sanitization:** Repository names and number inputs are validated before
   any GitHub request is made.
2. **Error disclosure protection:** Client errors do not expose tokens, upstream
   response bodies, private paths, or low-level exception details.

Run both exploit demonstrations:

```sh
python security_demo.py
```

Run the automated tests:

```sh
python -m unittest discover -v
```

## References

- [Official MCP Python SDK example](https://github.com/modelcontextprotocol/python-sdk/blob/v1.x/examples/snippets/servers/fastmcp_quickstart.py) — FastMCP decorators and `stdio` server pattern.
- [GitHub Pull Requests REST API](https://docs.github.com/en/rest/pulls/pulls) — pull request endpoints and authentication requirements.
