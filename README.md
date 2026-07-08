# File-Ops Agent with LangGraph

A command-line agent that reads, writes, searches, and edits files through natural language commands, built with [LangGraph](https://langchain-ai.github.io/langgraph/) and [LangChain](https://python.langchain.com/). The agent is strictly sandboxed to a single directory and cannot access paths outside it.

## What it does

```text
> Read the first 5 lines of notes.txt
> Append "Action item: send follow-up email" to notes.txt
> Replace "send" with "draft" in notes.txt
> Find all lines containing "Action item" in notes.txt
```

The agent decides which file operation to call, executes it inside `./sandbox`, and returns a natural-language answer.

## Architecture

```
START → agent (LLM) → [has tool calls?] → tools (execute) → agent (LLM) → END
                        [no tool calls?] → END
```

- `src/tools.py` — plain Python file tools and the sandbox path resolver.
- `src/agent.py` — LangGraph graph, tool schemas, and system prompt.
- `src/config.py` — sandbox root, max file size, forbidden path patterns.
- `src/logger.py` — JSON run logging.
- `main.py` — CLI with REPL and single-query mode.

## Quick start

1. Clone the repo and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Set your OpenAI API key:

```bash
export OPENAI_API_KEY="your-key-here"
# Optional: override the model
export OPENAI_MODEL="gpt-4o-mini"
```

3. Run a single query:

```bash
python main.py "list files in sandbox"
```

4. Or start the interactive REPL:

```bash
python main.py
```

## Tools

| Tool | Purpose |
|------|---------|
| `file_read` | Read full files, line ranges, or regex-filtered lines. |
| `file_write` | Overwrite or append content to a file. |
| `editor` | `str_replace` or `insert_at_line`. |
| `list_dir` | List files and directories inside the sandbox. |
| `mkdir` | Create directories inside the sandbox. |

## Safety

All paths are resolved through `resolve_path` in `src/tools.py`:

- Paths are anchored to `./sandbox`.
- Directory traversal (`../`), symlinks that escape, and absolute paths outside the sandbox are rejected.
- Known-sensitive patterns are blocked: `/etc`, `/usr`, `/bin`, `/sbin`, `/var`, `/opt`, `/root`, `.ssh`, `.bashrc`, `.env`.
- Reads and writes are capped at `MAX_FILE_SIZE` (1 MB by default).
- Tool errors are returned as strings starting with `Error:` rather than crashing the agent loop.

## CLI options

```bash
python main.py "read notes.txt"      # single query
python main.py -v "read notes.txt"   # single query with tool-call trace
python main.py                       # interactive REPL
```

## Logging

Every run is written as a JSON file under `logs/runs/` containing:

- query
- full message history
- final response
- latency
- error, if any

## Project layout

```
file-ops-agent-langgraph/
├── README.md
├── AGENTS.md             # How the AI coach works with the human
├── PLAN.md               # Build plan and acceptance criteria
├── requirements.txt
├── main.py               # CLI runner
├── src/
│   ├── __init__.py
│   ├── config.py         # Sandbox path, model, limits
│   ├── tools.py          # file_read, file_write, editor, list_dir, mkdir
│   ├── agent.py          # LangGraph graph definition
│   └── logger.py         # JSON run logging
├── sandbox/              # Default allowed directory (gitignored)
└── logs/                 # Run logs (gitignored)
```

## Dependencies

- `langgraph`
- `langchain`, `langchain-openai`
- `pydantic`
- `python-dotenv`

See `requirements.txt` for pinned versions.

## Notes

- The default LLM is `gpt-4o-mini`. Set `OPENAI_MODEL` to override it.
- The agent does not currently ask for confirmation before destructive operations. This is acceptable for a local MVP but should be added before running on untrusted input.
- No `.env` file is committed; manage secrets via environment variables.
