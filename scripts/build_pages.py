#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import os
import re
import shutil
from pathlib import Path

import markdown


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "site"
SKIP_PARTS = {
    ".git",
    ".github",
    ".pytest_cache",
    ".tmp",
    ".venv",
    "__pycache__",
    "benchmark-runs",
    "site",
    "tests",
    "venv",
}
SKIP_PREFIXES = {("docs", "plans")}
MARKDOWN_LINK_RE = re.compile(r"(!?\[[^\]]*\]\()([^)]+)(\))")
TITLE_RE = re.compile(r"^\s*#\s+(.+?)\s*$", re.MULTILINE)
REPO_ROOT_MARKDOWN = [
    "README.md",
    "CONTRIBUTING.md",
    "NOTICE.md",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
]


def is_skipped(path: Path) -> bool:
    try:
        parts = path.relative_to(ROOT).parts
    except ValueError:
        parts = path.parts
    if any(part in SKIP_PARTS for part in parts):
        return True
    return any(
        tuple(parts[index:index + len(prefix)]) == prefix
        for prefix in SKIP_PREFIXES
        for index in range(max(len(parts) - len(prefix) + 1, 0))
    )


def iter_markdown_sources() -> list[Path]:
    docs: set[Path] = {ROOT / rel for rel in REPO_ROOT_MARKDOWN}
    docs.update(ROOT.glob("s[0-9][0-9]_*/README.md"))
    docs.update(ROOT.glob("examples/**/*.md"))
    docs.update(path for path in ROOT.glob("docs/**/*.md") if not is_skipped(path))
    return sorted(path for path in docs if path.exists() and not is_skipped(path))


def route_for_markdown(path: Path) -> str:
    rel = path.relative_to(ROOT)
    if rel.as_posix() == "README.md":
        return "/"
    if rel.name == "README.md":
        return "/" + rel.parent.as_posix().strip("/") + "/"
    if len(rel.parts) == 1:
        return "/" + rel.stem.lower().replace("_", "-") + "/"
    return "/" + rel.with_suffix("").as_posix().strip("/") + "/"


def output_path_for_route(output_dir: Path, route: str) -> Path:
    if route == "/":
        return output_dir / "index.html"
    return output_dir / route.strip("/") / "index.html"


def read_title(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = TITLE_RE.search(text)
    if match:
        return match.group(1).strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


def split_link_target(target: str) -> tuple[str, str]:
    if "#" not in target:
        return target, ""
    path_part, anchor = target.split("#", 1)
    return path_part, "#" + anchor


def is_external_target(target: str) -> bool:
    lowered = target.lower()
    return lowered.startswith(("http://", "https://", "mailto:", "tel:", "data:"))


def to_root_relative(path: Path) -> str:
    return "/" + path.relative_to(ROOT).as_posix()


def resolve_local_target(source: Path, target: str) -> Path | None:
    candidate = (source.parent / target).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        return None
    return candidate


def rewrite_link_target(target: str, source: Path, routes: dict[Path, str]) -> str:
    target = target.strip()
    if not target or is_external_target(target) or target.startswith("#"):
        return target
    path_part, anchor = split_link_target(target)
    if not path_part:
        return anchor or target
    if path_part.startswith("/"):
        return path_part + anchor

    resolved = resolve_local_target(source, path_part)
    if resolved is None:
        return target

    if resolved.is_dir():
        readme = resolved / "README.md"
        if readme in routes:
            return routes[readme] + anchor
        return to_root_relative(resolved).rstrip("/") + "/" + anchor

    if resolved in routes:
        return routes[resolved] + anchor

    if resolved.exists():
        return to_root_relative(resolved) + anchor

    if resolved.suffix == "" and resolved.with_suffix(".md") in routes:
        return routes[resolved.with_suffix(".md")] + anchor

    return target


def rewrite_markdown_links(text: str, source: Path, routes: dict[Path, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        prefix, target, suffix = match.groups()
        return prefix + rewrite_link_target(target, source, routes) + suffix

    return MARKDOWN_LINK_RE.sub(replace, text)


def build_markdown_html(text: str) -> str:
    engine = markdown.Markdown(
        extensions=["extra", "admonition", "codehilite", "toc"],
        extension_configs={"toc": {"permalink": True}},
    )
    return engine.convert(text)


def source_url_for(path: Path) -> str | None:
    repo = os.environ.get("GITHUB_REPOSITORY")
    ref_name = os.environ.get("GITHUB_REF_NAME") or os.environ.get("GITHUB_SHA")
    if not repo or not ref_name:
        return None
    rel = path.relative_to(ROOT).as_posix()
    return f"https://github.com/{repo}/blob/{ref_name}/{rel}"


def build_nav(title_map: dict[Path, str], routes: dict[Path, str]) -> str:
    def link_item(label: str, route: str) -> str:
        return f'<li><a href="{route}">{html.escape(label)}</a></li>'

    parts = [
        '<nav class="sidebar">',
        '<div class="brand"><a href="/">learn-workbuddy</a></div>',
        '<div class="nav-group"><div class="nav-title">开始阅读</div><ul>',
    ]
    quick_paths = [
        ROOT / "README.md",
        ROOT / "docs" / "learning-guide.md",
        ROOT / "docs" / "visual-tour.md",
        ROOT / "docs" / "chapter-map.md",
    ]
    for path in quick_paths:
        if path in routes:
            parts.append(link_item(title_map[path], routes[path]))
    parts.append("</ul></div>")

    chapters = sorted(path for path in routes if path.match(str(ROOT / "s[0-9][0-9]_*" / "README.md")))
    parts.append('<div class="nav-group"><div class="nav-title">24 章课程</div><ul>')
    for path in chapters:
        parts.append(link_item(title_map[path], routes[path]))
    parts.append("</ul></div>")

    docs = sorted(
        path for path in routes
        if path.parent == ROOT / "docs"
        and path.name not in {"learning-guide.md", "visual-tour.md", "chapter-map.md"}
    )
    if docs:
        parts.append('<div class="nav-group"><div class="nav-title">补充文档</div><ul>')
        for path in docs:
            parts.append(link_item(title_map[path], routes[path]))
        parts.append("</ul></div>")

    examples = sorted(path for path in routes if "examples" in path.parts)
    if examples:
        parts.append('<div class="nav-group"><div class="nav-title">示例</div><ul>')
        for path in examples:
            parts.append(link_item(title_map[path], routes[path]))
        parts.append("</ul></div>")

    project_docs = sorted(
        path for path in routes
        if path.parent == ROOT and path.name != "README.md"
    )
    if project_docs:
        parts.append('<div class="nav-group"><div class="nav-title">项目文档</div><ul>')
        for path in project_docs:
            parts.append(link_item(title_map[path], routes[path]))
        parts.append("</ul></div>")

    parts.append("</nav>")
    return "\n".join(parts)


def page_template(*, page_title: str, content: str, nav: str, source_url: str | None) -> str:
    source_html = ""
    if source_url:
        source_html = (
            '<p class="source-link"><a href="'
            + html.escape(source_url)
            + '" target="_blank" rel="noreferrer">查看源码</a></p>'
        )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(page_title)} | learn-workbuddy</title>
  <link rel="stylesheet" href="/assets/site.css">
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
    mermaid.initialize({{ startOnLoad: false, theme: "neutral" }});
    window.addEventListener("DOMContentLoaded", async () => {{
      document.querySelectorAll("pre code.language-mermaid").forEach((codeBlock) => {{
        const wrapper = document.createElement("div");
        wrapper.className = "mermaid";
        wrapper.textContent = codeBlock.textContent || "";
        codeBlock.parentElement.replaceWith(wrapper);
      }});
      await mermaid.run({{ querySelector: ".mermaid" }});
    }});
  </script>
</head>
<body>
  <div class="layout">
    {nav}
    <main class="content-shell">
      <header class="page-header">
        <h1>{html.escape(page_title)}</h1>
        {source_html}
      </header>
      <article class="markdown-body">
        {content}
      </article>
    </main>
  </div>
</body>
</html>
"""


def write_assets(output_dir: Path) -> None:
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "site.css").write_text(
        """\
:root {
  color-scheme: light;
  --bg: #f6f8fb;
  --panel: #ffffff;
  --border: #d8dee9;
  --text: #1f2937;
  --muted: #6b7280;
  --link: #2563eb;
  --code-bg: #0f172a;
  --code-fg: #e2e8f0;
}

* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg);
  color: var(--text);
}
a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }
.layout { display: grid; grid-template-columns: 300px minmax(0, 1fr); min-height: 100vh; }
.sidebar {
  position: sticky;
  top: 0;
  align-self: start;
  height: 100vh;
  overflow-y: auto;
  padding: 24px 18px 48px;
  background: #0f172a;
  color: #e5e7eb;
}
.brand a { color: #ffffff; font-size: 1.25rem; font-weight: 700; }
.nav-group { margin-top: 24px; }
.nav-title {
  margin-bottom: 8px;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #94a3b8;
}
.nav-group ul { margin: 0; padding: 0; list-style: none; }
.nav-group li { margin: 0 0 8px; }
.nav-group a { color: #dbeafe; line-height: 1.4; }
.content-shell {
  max-width: 1100px;
  padding: 32px 40px 64px;
}
.page-header {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 20px;
}
.page-header h1 { margin: 0; font-size: 2rem; }
.source-link { margin: 0; color: var(--muted); }
.markdown-body {
  padding: 32px;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 20px;
  box-shadow: 0 10px 35px rgba(15, 23, 42, 0.08);
}
.markdown-body img {
  max-width: 100%;
  height: auto;
  border-radius: 12px;
}
.markdown-body table {
  display: block;
  overflow-x: auto;
  width: 100%;
  border-collapse: collapse;
}
.markdown-body th,
.markdown-body td {
  padding: 10px 12px;
  border: 1px solid var(--border);
  vertical-align: top;
}
.markdown-body pre {
  overflow-x: auto;
  padding: 16px;
  border-radius: 14px;
  background: var(--code-bg);
  color: var(--code-fg);
}
.markdown-body code {
  font-family: "Cascadia Code", Consolas, monospace;
}
.markdown-body :not(pre) > code {
  padding: 0.15rem 0.35rem;
  border-radius: 6px;
  background: #e5e7eb;
  color: #111827;
}
.markdown-body blockquote {
  margin: 1rem 0;
  padding: 0.1rem 1rem;
  border-left: 4px solid #93c5fd;
  color: #334155;
  background: #eff6ff;
}
.mermaid {
  overflow-x: auto;
  margin: 1.5rem 0;
}
@media (max-width: 980px) {
  .layout { grid-template-columns: 1fr; }
  .sidebar {
    position: static;
    height: auto;
  }
  .content-shell {
    padding: 20px 16px 40px;
  }
  .markdown-body {
    padding: 20px;
    border-radius: 16px;
  }
}
""",
        encoding="utf-8",
    )


def copy_static_files(output_dir: Path) -> None:
    for path in ROOT.rglob("*"):
        if path.is_dir() or is_skipped(path):
            continue
        rel = path.relative_to(ROOT)
        destination = output_dir / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def build_site(output_dir: Path = DEFAULT_OUTPUT) -> Path:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    markdown_sources = iter_markdown_sources()
    routes = {path.resolve(): route_for_markdown(path.resolve()) for path in markdown_sources}
    title_map = {path.resolve(): read_title(path.resolve()) for path in markdown_sources}
    nav = build_nav(title_map, routes)

    copy_static_files(output_dir)
    write_assets(output_dir)

    for path in markdown_sources:
        source = path.resolve()
        text = source.read_text(encoding="utf-8")
        rewritten = rewrite_markdown_links(text, source, routes)
        content = build_markdown_html(rewritten)
        page = page_template(
            page_title=title_map[source],
            content=content,
            nav=nav,
            source_url=source_url_for(source),
        )
        destination = output_path_for_route(output_dir, routes[source])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(page, encoding="utf-8")

    shutil.copy2(output_dir / "index.html", output_dir / "404.html")
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a static GitHub Pages site for learn-workbuddy.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Static site output directory.",
    )
    args = parser.parse_args()
    output_dir = build_site(args.output)
    print(f"Built pages site at {output_dir}")


if __name__ == "__main__":
    main()
