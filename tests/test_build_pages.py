from __future__ import annotations

from pathlib import Path

from scripts.build_pages import (
    build_site,
    detect_base_path,
    rewrite_link_target,
    route_for_markdown,
    with_base_path,
)


def test_route_for_markdown_handles_root_chapters_and_docs(root: Path) -> None:
    assert route_for_markdown(root / "README.md") == "/"
    assert route_for_markdown(root / "s01_agent_loop" / "README.md") == "/s01_agent_loop/"
    assert route_for_markdown(root / "docs" / "learning-guide.md") == "/docs/learning-guide/"


def test_rewrite_link_target_maps_markdown_and_assets(root: Path) -> None:
    routes = {
        (root / "README.md").resolve(): "/",
        (root / "docs" / "learning-guide.md").resolve(): "/docs/learning-guide/",
        (root / "s01_agent_loop" / "README.md").resolve(): "/s01_agent_loop/",
    }
    source = (root / "README.md").resolve()

    assert rewrite_link_target("./s01_agent_loop/", source, routes) == "/s01_agent_loop/"
    assert rewrite_link_target("./docs/learning-guide.md", source, routes) == "/docs/learning-guide/"
    assert rewrite_link_target("./images/architecture-overview.svg", source, routes) == "/images/architecture-overview.svg"
    assert rewrite_link_target("./LICENSE", source, routes) == "/LICENSE"


def test_detect_base_path_for_project_pages(monkeypatch) -> None:
    monkeypatch.delenv("PAGES_BASE_PATH", raising=False)
    monkeypatch.delenv("SITE_BASE_PATH", raising=False)
    monkeypatch.setenv("GITHUB_REPOSITORY", "a-persimmons/learn-workbuddy")
    assert detect_base_path() == "/learn-workbuddy/"


def test_with_base_path_prefixes_project_pages_route() -> None:
    assert with_base_path("/assets/site.css", "/learn-workbuddy/") == "/learn-workbuddy/assets/site.css"
    assert with_base_path("/s01_agent_loop/", "/learn-workbuddy/") == "/learn-workbuddy/s01_agent_loop/"
    assert with_base_path("/", "/learn-workbuddy/") == "/learn-workbuddy/"


def test_build_site_generates_core_pages(root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "a-persimmons/learn-workbuddy")
    output_dir = build_site(tmp_path / "site")

    home = (output_dir / "index.html").read_text(encoding="utf-8")
    chapter = (output_dir / "s01_agent_loop" / "index.html").read_text(encoding="utf-8")
    guide = (output_dir / "docs" / "learning-guide" / "index.html").read_text(encoding="utf-8")

    assert "learn-workbuddy" in home
    assert 'href="/learn-workbuddy/s01_agent_loop/"' in home
    assert 'href="/learn-workbuddy/assets/site.css"' in home
    assert "language-mermaid" in chapter
    assert "<h1>Learning Guide</h1>" in guide
