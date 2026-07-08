from __future__ import annotations

import argparse
import os
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from anthropic import Anthropic
from dotenv import load_dotenv

from mini_workbuddy.audit import AuditLog
from mini_workbuddy.agent import MiniAgent
from mini_workbuddy.config import HarnessConfig
from mini_workbuddy.events import EventBus
from mini_workbuddy.storage import Storage
from mini_workbuddy.tools import ToolRegistry


REAL_API_PROMPT = (
    "Use the available tools to inspect this project. First list available tools, "
    "then run pwd, then read README.md, then summarize what this WorkBuddy-style "
    "harness demo proves in three concise bullets."
)

TOOL_SCHEMAS = [
    {
        "name": "tool_search",
        "description": "List or search available harness tools.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
        },
    },
    {
        "name": "bash",
        "description": "Run a shell command in the session cwd. Dangerous commands are denied.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a UTF-8 text file by cwd-relative path.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
]


def build_runtime() -> tuple[HarnessConfig, Storage, EventBus, AuditLog, ToolRegistry]:
    config = HarnessConfig.from_env()
    storage = Storage(config)
    events = EventBus()
    audit = AuditLog(config)
    tools = ToolRegistry(config, storage)
    return config, storage, events, audit, tools


def run_offline_demo() -> None:
    _, storage, events, audit, tools = build_runtime()
    agent = MiniAgent(storage, tools, events, audit)

    session = storage.create_session(cwd=str(ROOT), title="mini workbuddy full demo")
    memory_path = storage.append_memory(
        "workspace",
        "- Mini demo memory: explain harness mechanics before product polish.",
    )

    print("Session:", session.id)
    print("Workspace:", session.cwd)
    print("Memory:", memory_path)

    prompts = [
        ("tool directory", "tools"),
        ("current directory", "pwd"),
        ("read project readme", "read README.md"),
        ("permission denial", "bash rm -rf ."),
        ("large output externalization", "bash python3 -c \"print('x' * 70000)\""),
    ]

    for label, prompt in prompts:
        print("\n" + "=" * 72)
        print(f"{label}: {prompt}")
        result = agent.prompt(session, prompt)
        print(result["answer"][:1200])
        for tool_result in result["toolResults"]:
            externalized = tool_result.get("externalized_path")
            if externalized:
                print("Externalized:", externalized)

    transcript = storage.read_transcript(session)
    sessions = storage.list_sessions()

    print("\n" + "=" * 72)
    print("Recovered state")
    print("Transcript:", storage.transcript_path(session))
    print("Transcript events:", len(transcript))
    print("Known sessions:", len(sessions))
    print("Workspace memory:")
    print(storage.read_memory("workspace").strip())

    print("\n" + "=" * 72)
    print("Audit")
    print("Audit file:", audit.path)
    print("Audit entries:", len(audit.read_entries()))
    print("Audit verified:", audit.verify())


def api_env_ready() -> bool:
    load_dotenv(override=True)
    return bool(os.getenv("ANTHROPIC_API_KEY") and os.getenv("MODEL_ID"))


def run_real_api_demo(prompt: str, max_turns: int = 8) -> None:
    load_dotenv(override=True)
    if os.getenv("ANTHROPIC_BASE_URL"):
        os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
    if not api_env_ready():
        raise SystemExit(
            "Real API demo requires ANTHROPIC_API_KEY and MODEL_ID. "
            "Copy .env.example to .env, fill them, then rerun with --mode real."
        )

    _, storage, events, audit, tools = build_runtime()
    client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
    model = os.environ["MODEL_ID"]
    session = storage.create_session(cwd=str(ROOT), title="mini workbuddy real api demo")
    storage.append_memory(
        "workspace",
        "- Real API demo: model must use tools through the mini harness.",
    )

    system = (
        f"You are Mini WorkBuddy running in {session.cwd}. "
        "For this teaching demo, use tools instead of answering from memory. "
        "Call tool_search, bash, and read_file when useful. "
        "The harness records transcript, memory, tool results, and audit entries."
    )
    messages: list[dict] = [{"role": "user", "content": prompt}]
    storage.append_event(session, {"type": "message", "role": "user", "content": prompt})
    audit.append("user_prompt", {"sessionId": session.id, "text": prompt})

    print("Mode: real API")
    print("Model:", model)
    print("Session:", session.id)
    print("Workspace:", session.cwd)
    print("Prompt:", prompt)

    final_text = ""
    for turn in range(1, max_turns + 1):
        print("\n" + "=" * 72)
        print(f"model turn {turn}")
        response = client.messages.create(
            model=model,
            system=system,
            messages=messages,
            tools=TOOL_SCHEMAS,
            max_tokens=4000,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        saw_tool = False
        for block in response.content:
            if block.type == "text":
                final_text += block.text
                print(block.text)
                continue
            if block.type != "tool_use":
                continue
            saw_tool = True
            tool_name = block.name
            argument = tool_argument(tool_name, block.input)
            print(f"[tool_use] {tool_name}: {argument}")
            audit.append(
                "tool_call",
                {"sessionId": session.id, "tool": tool_name, "argument": argument},
            )
            result = tools.run(tool_name, argument, session)
            storage.append_event(session, {"type": "tool_result", **asdict(result)})
            events.publish(
                "session_update",
                {"sessionId": session.id, "type": "tool_result", **asdict(result)},
            )
            audit.append(
                "tool_result",
                {
                    "sessionId": session.id,
                    "tool": result.name,
                    "externalized": result.externalized_path is not None,
                    "exit_code": result.exit_code,
                },
            )
            preview = result.content[:1000]
            print(preview)
            if result.externalized_path:
                print("Externalized:", result.externalized_path)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result.content,
            })

        if not saw_tool:
            storage.append_event(session, {"type": "message", "role": "assistant", "content": final_text})
            audit.append("assistant_message", {"sessionId": session.id, "content": final_text[:500]})
            break
        messages.append({"role": "user", "content": tool_results})
    else:
        print("\nReached max turns before the model stopped calling tools.")

    transcript = storage.read_transcript(session)
    print("\n" + "=" * 72)
    print("Recovered state")
    print("Transcript:", storage.transcript_path(session))
    print("Transcript events:", len(transcript))
    print("Audit file:", audit.path)
    print("Audit entries:", len(audit.read_entries()))
    print("Audit verified:", audit.verify())


def tool_argument(tool_name: str, tool_input: dict) -> str:
    if tool_name == "bash":
        return str(tool_input.get("command", ""))
    if tool_name == "read_file":
        return str(tool_input.get("path", ""))
    if tool_name == "tool_search":
        return str(tool_input.get("query", ""))
    raise KeyError(f"unknown tool: {tool_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mini WorkBuddy demo")
    parser.add_argument(
        "--mode",
        choices=["auto", "offline", "real"],
        default="auto",
        help="auto uses real API when ANTHROPIC_API_KEY and MODEL_ID exist, otherwise offline",
    )
    parser.add_argument("--prompt", default=REAL_API_PROMPT, help="prompt for --mode real")
    parser.add_argument("--max-turns", type=int, default=8)
    args = parser.parse_args()

    if args.mode == "offline":
        print("Mode: offline deterministic harness")
        run_offline_demo()
        return
    if args.mode == "real":
        run_real_api_demo(args.prompt, args.max_turns)
        return
    if api_env_ready():
        run_real_api_demo(args.prompt, args.max_turns)
        return

    print("Mode: auto -> no ANTHROPIC_API_KEY/MODEL_ID found, running offline deterministic harness.")
    print("For the real API path: cp .env.example .env, fill it, then run:")
    print("  python3 examples/mini_workbuddy_demo/code.py --mode real\n")
    run_offline_demo()


if __name__ == "__main__":
    main()
