import os
from typing import Annotated, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

from src.tools import editor, file_read, file_write, list_dir, mkdir

SYSTEM_PROMPT = """You are a careful file-operations assistant that works inside a sandbox directory.

Rules:
- All file paths are resolved inside ./sandbox. Absolute paths only work if they already point under that directory.
- Paths with directory traversal (../ or /../), system directories (/etc, /usr, /bin, /sbin, /var, /opt, /root), or sensitive folders (.ssh, .bashrc, .env) are rejected.
- Read files before editing or overwriting whenever you need to preserve context.
- Make targeted edits with str_replace; use insert_at_line when you need to add new lines.
- Use list_dir to explore directories before reading unknown files.
- Use mkdir to create directories before writing files that need them.
- Stop and respond when the task is complete.
"""


@tool
def list_dir_tool(path: str = ".") -> str:
    """
    List files and directories inside a sandbox directory.

    Args:
        path: Sandbox-relative or absolute path to the directory to list. Default is the sandbox root (".").
        The path is resolved inside ./sandbox; absolute paths are allowed only if they already
        point under the sandbox, and paths that escape the sandbox or contain
        traversal fragments are rejected.

    Returns:
        A newline-separated list of entries, each prefixed with "file: " or
        "dir: ". Returns an error message starting with "Error:" if the path
        is invalid, does not exist, or is not a directory.
    """
    return list_dir(path)


@tool
def mkdir_tool(path: str) -> str:
    """
    Create a directory inside the sandbox.

    Args:
        path: Sandbox-relative or absolute path where the directory should be created, e.g. "data/backups".
        Intermediate directories are created automatically. The path is resolved inside ./sandbox; absolute
        paths are allowed only if they already point under the sandbox, and paths that escape the sandbox
        or contain traversal fragments are rejected.

    Returns:
        A success message, or an error message starting with "Error:" if the
        path is invalid, escapes the sandbox, or points to an existing file.
    """
    return mkdir(path)


@tool
def file_read_tool(path: str, offset: int = 1, limit: int = 0, search: str = "") -> str:
    """
    Read lines from a sandboxed file inside ./sandbox.

    This tool reads text from a file located inside the sandbox. It can return the
    whole file, a specific range of lines, or filter the selected range by a
    regular expression.

    Args:
        path: Sandbox-relative or absolute path to the file to read, e.g.
            "src/main.py" or "docs/README.md". The path is resolved inside
            ./sandbox; absolute paths are allowed only if they already point
            under the sandbox, and paths that escape the sandbox (e.g. "../")
            are rejected.
        offset: 1-indexed line number to start reading from. Default is 1 (the
            first line). For example, offset=10 starts at line 10. Values below
            1 are clamped to 1.
        limit: Maximum number of lines to return after `offset`. Use 0 (the
            default) to read from `offset` to the end of the file. Use a positive
            number to cap the output, e.g. limit=20 returns at most 20 lines.
        search: Optional Python regular expression. When provided, only lines in
            the already selected offset/limit range that match the pattern are
            returned. The regex is NOT applied to the whole file first; the file
            is sliced first and then filtered. Leave empty to skip filtering.

    Returns:
        A string containing the requested lines, joined with newline characters.
        Returns an error message starting with "Error:" if the path is invalid,
        escapes the sandbox, points to a directory, the file does not exist, or
        the file is larger than the configured maximum size.
    """
    return file_read(path, offset, limit, search)


@tool
def file_write_tool(path: str, content: str, mode: Literal["overwrite", "append"] = "overwrite") -> str:
    """
    Write content to a file inside ./sandbox.

    This tool creates a new file or updates an existing file at the given sandbox
    path. Parent directories are created automatically if needed.

    Args:
        path: Sandbox-relative or absolute path where the file should be written,
            e.g. "src/utils.py" or "data/output.json". The path is resolved
            inside ./sandbox; absolute paths are allowed only if they already point
            under the sandbox, and paths that escape the sandbox are rejected.
            Intermediate directories are created automatically.
        content: The text to write into the file. Should be a complete, valid
            string for the target file type. Must not exceed the configured
            maximum file size.
        mode: Write mode. Must be one of:
            - "overwrite" (default): Replace the entire file with `content`.
            - "append": Add `content` to the end of the file. If the existing
              file does not end with a newline, one is inserted before `content`.
              The resulting file must not exceed the configured maximum size.

    Returns:
        A status message indicating success, or an error message starting with
        "Error:" if the path is invalid, escapes the sandbox, is a directory,
        or an unsupported mode is used.
    """
    return file_write(path, content, mode)


@tool
def editor_tool(path: str, command: Literal["str_replace", "insert_at_line"], old_str: str = "", new_str: str = "", line: int = 0) -> str:
    """
    Edit a file inside ./sandbox using a structured editor command.

    This tool performs precise text edits on an existing sandbox file. It supports
    replacing the first occurrence of a substring, or inserting a new line after
    a specific 1-indexed line.

    Args:
        path: Sandbox-relative or absolute path to the file to edit, e.g.
            "src/app.py". The path is resolved inside ./sandbox; absolute paths
            are allowed only if they already point under the sandbox, and paths
            that escape the sandbox are rejected.
        command: The edit operation to perform. Must be one of:
            - "str_replace": Replace the first occurrence of `old_str` with
              `new_str`. `old_str` must match exactly, including whitespace and
              indentation. Only the first match is changed.
            - "insert_at_line": Insert `new_str` as a new line immediately after
              the 1-indexed line given by `line`. Use line=0 or a value greater
              than or equal to the file length to append at the end of the file.
        old_str: Exact text to locate when using the "str_replace" command. Must
            be a non-empty, contiguous substring of the file as it currently
            exists. Ignored for "insert_at_line".
        new_str: Text to substitute or insert. Required for "str_replace" and
            "insert_at_line".
        line: 1-indexed line number used by the "insert_at_line" command. The new
            text is inserted AFTER this line. Values <= 0 or >= file length append
            to the end. Ignored for "str_replace".

    Returns:
        A status message describing the result of the edit, or an error message
        starting with "Error:" if the path is invalid, the file is missing, the
        command is unknown, the target text is not found, or the line number is
        out of range.
    """
    return editor(path, command, old_str, new_str, line)


tools = [file_read_tool, file_write_tool, editor_tool, list_dir_tool, mkdir_tool]


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    temperature=0,
)
llm_with_tools = llm.bind_tools(tools)

def agent_node(state: AgentState):
    response = llm_with_tools.invoke(state["messages"])
    return {
        "messages": [response]
    }


tool_node = ToolNode(tools)
graph_builder = StateGraph(AgentState)
graph_builder.add_node("agent", agent_node)
graph_builder.add_node("tools", tool_node)
graph_builder.add_edge(START, "agent")
graph_builder.add_conditional_edges("agent", tools_condition)
graph_builder.add_edge("tools", "agent")

graph = graph_builder.compile()


if __name__ == "__main__":
    for t in tools:
        print(t.name)
        print(t.description)
        print(t.args)
        print("-" * 40)
