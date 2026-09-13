# Development Workflow: PR Review Assistant

Part 1 of Assignment 4: a Python MCP server exposing **two tools and one prompt**.
The server retrieves GitHub data; the connected model performs the review.
It does not require a separate LLM API key.

| MCP endpoint | Purpose |
| --- | --- |
| `list_open_pull_requests` (tool) | Discover open PRs in a repository, with pagination. |
| `get_pull_request_details` (tool) | Retrieve one PR's metadata and changed-file patch excerpts. |
| `review_pull_request` (prompt) | Guide a model through an evidence-based review using the details tool. |

Discovery and inspection are separate tools because they answer different questions
and return different amounts of data. The prompt defines how to use the retrieved
evidence; it does not call the tools or review code by itself.

## Setup

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).
From this directory:

```sh
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env
```

In VS Code, select `.venv/bin/python` with **Python: Select Interpreter**.
Activate the environment in the integrated terminal with the command above.

Create a GitHub fine-grained personal access token for the repositories you plan
to review, with **Pull requests: Read-only** permission. Put it in `.env`:

```dotenv
GITHUB_TOKEN=your_token_here
```

The server reads `.env` using `pathlib.Path` and `dotenv_values`; it does not read
the token from shell environment variables. `.env` is ignored by Git. Do not paste
the token into chat or commit it. Both tools require a token, including for public
repositories, so authentication is explicit for the assignment.

## Run

```sh
python server.py
```

The server uses stdio: it waits for an MCP client and does not display a web page
or a startup message on stdout. Press Ctrl+C to stop it. An MCP client should
launch `.venv/bin/python` with the absolute path to `server.py` as its argument.
The `.env` path is resolved relative to the source, regardless of client working
directory.

## Connect Claude Desktop (macOS)

The included `claude_desktop_config.json` contains the exact paths for this
machine. On another machine, update both paths to its project location.

1. Open Claude Desktop, then **Claude → Settings → Developer → Edit Config**.
2. Add the `mcpServers` entry from this project's `claude_desktop_config.json`
   to `~/Library/Application Support/Claude/claude_desktop_config.json`.
   Preserve any existing settings and MCP servers. The copy in this project
   is a configuration example; Claude reads the copy in Application Support.
3. Save, fully quit Claude with **Cmd+Q**, and reopen it.
4. Check **Settings → Developer** for `pr-review-assistant`. In a new chat,
   enable its tools through the connectors menu if needed, then ask:
   **Use pr-review-assistant to list open pull requests in vidhu-hegde/Fork-Fly,
   then fetch the details of PR #1.**

Claude launches the server automatically; no terminal server process is needed.
The token stays in the project's `.env`, not in the Claude configuration.
If startup fails, inspect `~/Library/Logs/Claude/mcp-server-pr-review-assistant.log`.
See the [official local-server setup guide](https://modelcontextprotocol.io/docs/develop/connect-local-servers).

## Part 2 security best practices

The server implements the following two required practices:

| Practice | Protection | Exploit demonstration |
| --- | --- | --- |
| Input sanitization | Full-string allowlists constrain `owner` and `repo`; strict integer checks constrain PR and pagination values. Validation happens before URL construction or any HTTP request. | A repository value containing path traversal and a query string is rejected, and a mock proves the HTTP client was never called. |
| Error disclosure protection | GitHub response bodies and low-level network exception messages are replaced with short, actionable errors. Tokens are never included in returned errors. | A simulated HTTP 500 body contains a fake token and private path; neither appears in the client-facing exception. |

Run the demo from the activated virtual environment:

```sh
python security_demo.py
```

Expected result:

```text
PASS 1 - Input sanitization
  Proof: no HTTP request was made.
PASS 2 - Error disclosure protection
  Proof: the fake token, private path, and response body are absent.

Both Part 2 exploit demonstrations passed.
```

The demo is deterministic and makes no network calls. It uses clearly fake
credentials and mocked GitHub responses, so it is safe to show in class. Run
the broader automated checks with:

```sh
python -m unittest discover -v
```

For the live Claude Desktop portion, malicious values such as
`Fork-Fly/../../user?access_token=steal-me` can be passed as `repo`; the tool
returns `repo must be a repository name, not a path or URL.` The standalone
demo supplies stronger evidence by also proving no outbound request occurred.

## Example calls

Use a repository and PR number you have access to:

```json
{"owner": "YOUR_OWNER", "repo": "YOUR_REPO", "page": 1, "per_page": 10}
```

Pass those arguments to `list_open_pull_requests`, then use one returned number:

```json
{"owner": "YOUR_OWNER", "repo": "YOUR_REPO", "pull_number": 1, "file_page": 1}
```

Pass those arguments to `get_pull_request_details`. For the `review_pull_request`
prompt, provide `owner`, `repo`, and `pull_number` as strings (for example `"1"`).
The client retrieves the prompt and passes it to its model; the model can then
request tool calls. This server only reads GitHub data and never posts reviews.

## Files and limitations

- `server.py`: MCP registration, typed tool interfaces, and review prompt.
- `github_client.py`: input checks, `.env` authentication, GitHub requests, and output shaping.
- `security_demo.py`: safe, repeatable exploit demonstrations for both practices.
- `tests/test_security.py`: automated security regression checks.
- `requirements.txt`: dependencies constrained to the official MCP SDK 1.x API.
- `.env.example`: blank credential template.

File results are paginated in groups of ten. Each patch is capped at 6,000
characters and the PR description at 6,000 characters, with truncation flags.
GitHub may omit patches and limits its PR-files endpoint to 3,000 files. The
server does not retrieve whole source files, CI results, review comments, or run
tests. Results are live API reads, not an atomic snapshot. Compare `head_sha`
across pages to notice some changes during a review.

Missing credentials, access failures, rate-limit responses, and connection
problems produce actionable errors without returning upstream response bodies
or low-level exception details.

## References

- [Official MCP Python SDK 1.x](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x): FastMCP registration and stdio pattern, attributed in `server.py`.
- [GitHub pull-request API](https://docs.github.com/en/rest/pulls/pulls): endpoint contracts, pagination, authentication permissions, and file limits.
- [uv installation](https://docs.astral.sh/uv/getting-started/installation/): virtual-environment tooling.

The implementation is project-specific; no third-party server implementation
was copied. Assignment submission reflections and the Canvas documentation are
not included here.
