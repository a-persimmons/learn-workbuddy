"""Shared chapter demo helpers.

The 24 lesson files are intentionally small, standalone scripts. This
module gives them a common learning entrypoint without moving their core
code into a framework:

    python s01_agent_loop/code.py --demo
    python s01_agent_loop/code.py --provider deepseek

`--demo` is offline and keyless. `--provider deepseek` maps DeepSeek's
Anthropic-compatible API into the environment variables the earlier
chapters already understand.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


def _load_env(*, override: bool = True) -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    load_dotenv(override=override)


def _apply_deepseek_env() -> None:
    key = os.getenv("DEEPSEEK_API_KEY")
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key
    os.environ["ANTHROPIC_BASE_URL"] = os.getenv(
        "DEEPSEEK_BASE_URL",
        "https://api.deepseek.com/anthropic",
    )
    os.environ["MODEL_ID"] = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)


def _patch_dotenv_for_provider(provider: str) -> None:
    """Keep later chapter-local load_dotenv calls from undoing provider mapping."""
    if provider != "deepseek":
        return
    try:
        import dotenv
    except Exception:
        return
    original = dotenv.load_dotenv

    def patched_load_dotenv(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **kwargs)
        _apply_deepseek_env()
        return result

    dotenv.load_dotenv = patched_load_dotenv


def _take_provider_arg(argv: list[str]) -> str | None:
    provider: str | None = None
    cleaned: list[str] = [argv[0]]
    i = 1
    while i < len(argv):
        item = argv[i]
        if item == "--provider":
            if i + 1 >= len(argv):
                raise SystemExit("--provider requires: anthropic | deepseek")
            provider = argv[i + 1]
            i += 2
            continue
        if item.startswith("--provider="):
            provider = item.split("=", 1)[1]
            i += 1
            continue
        cleaned.append(item)
        i += 1
    argv[:] = cleaned
    return provider


def prepare_chapter_provider() -> str:
    """Normalize provider flags for API-backed lesson scripts.

    Most lesson chapters were written against the Anthropic Messages API.
    DeepSeek's Anthropic-compatible endpoint lets readers use the same
    teaching code with only a DeepSeek key. This helper converts:

        --provider deepseek

    into the environment expected by those chapters, then removes the
    provider flag so chapter-specific argparse code remains simple.
    """

    _load_env()
    provider = (_take_provider_arg(sys.argv) or os.getenv("PROVIDER") or "anthropic").lower()
    if provider == "deepseek":
        _apply_deepseek_env()
        _patch_dotenv_for_provider(provider)
    elif provider == "anthropic":
        if os.getenv("ANTHROPIC_BASE_URL"):
            os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
    else:
        raise SystemExit("Lesson provider must be anthropic or deepseek.")
    return provider


def maybe_run_chapter_demo(file: str, progression: dict[str, Any]) -> None:
    """Run the offline chapter demo and exit when --demo is present."""

    if "--demo" not in sys.argv:
        return
    sys.argv[:] = [arg for arg in sys.argv if arg != "--demo"]
    run_chapter_demo(file, progression)
    raise SystemExit(0)


def run_chapter_demo(file: str, progression: dict[str, Any]) -> None:
    path = Path(file).resolve()
    chapter_dir = path.parent
    readme = chapter_dir / "README.md"
    title = chapter_dir.name
    if readme.exists():
        first = readme.read_text(encoding="utf-8", errors="ignore").splitlines()
        if first:
            title = first[0].lstrip("# ").strip()

    print(f"{title}")
    print("=" * len(title))
    print()
    print("这是离线学习 demo：不调用模型、不需要 API key，只说明本章在渐进链路中的位置。")
    print("要体验真实模型交互，配置 .env 后直接运行本章脚本。")
    print()

    builds_on = progression.get("builds_on") or []
    adds = progression.get("adds") or []
    preserves = progression.get("preserves") or []

    print("继承自:")
    print("  " + (", ".join(builds_on) if builds_on else "无，这是最小起点"))
    print()
    print("本章新增:")
    for item in adds:
        print(f"  - {item}")
    print()
    print("继续保留:")
    for item in preserves:
        print(f"  - {item}")

    if readme.exists():
        text = readme.read_text(encoding="utf-8", errors="ignore")
        has_arch = "## 代码架构图" in text and "```mermaid" in text
        has_image = "![" in text
        print()
        print("学习材料:")
        print(f"  - README: {readme.relative_to(path.parents[1])}")
        print(f"  - 代码架构图: {'有' if has_arch else '缺失'}")
        print(f"  - 配图: {'有' if has_image else '缺失'}")

    rel = path.relative_to(path.parents[1]).as_posix()
    print()
    print("在线体验:")
    print("  cp .env.example .env")
    print("  # 填 DEEPSEEK_API_KEY 后：")
    print(f"  python3 {rel} --provider deepseek")
    print()
    print("本章 demo 完成。")
