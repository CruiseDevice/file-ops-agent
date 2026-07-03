import argparse
import sys
import time

from langchain_core.messages import HumanMessage, SystemMessage

from src.agent import SYSTEM_PROMPT, graph
from src.logger import log_run


def run_agent(query: str, verbose: bool = False) -> str:
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=query)]
    start = time.perf_counter()
    error = None
    final_messages = messages
    try:
        result = graph.invoke(
            {"messages": messages},
            config={"recursion_limit": 10},
        )
        final_messages = result["messages"]
        final_response = final_messages[-1].content
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        final_response = f"Error: {error}"
    finally:
        latency = time.perf_counter() - start
        log_file = log_run(final_messages, final_response, latency, error)

        if verbose:
            print(f"Run logged to: {log_file}")
            _print_trace(final_messages)

    return final_response


def _print_trace(messages):
    for message in messages:
        if message.type == "system":
            continue
        if message.type == "human":
            print(f"User: {message.content}")
        elif message.type == "ai":
            if getattr(message, "tool_calls", None):
                for tc in message.tool_calls:
                    print(f"Tool call: {tc.get('name')}({tc.get('args')})")

            if message.content:
                print(f"Agent: {message.content}")

        elif message.type == "tool":
            snippet = message.content[:300]
            suffix = "..." if len(message.content) > 300 else ""
            print(f"Tool result: {snippet}{suffix}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sandbox file-ops agent")
    parser.add_argument("query", nargs="*", help="Single query to run (omit for REPL)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print tool-call trace")

    args = parser.parse_args(argv)

    if args.query:
        query = " ".join(args.query)
        print(run_agent(query, verbose=args.verbose))
        return 0

    print("File-ops agent. Type 'exit' or 'quit' to leave")
    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if query.lower() in {"exit", "quit"}:
            break
        if not query:
            continue

        print(run_agent(query, verbose=args.verbose))

    return 0
    
if __name__ == "__main__":
    sys.exit(main())
