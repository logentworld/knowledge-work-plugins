#!/usr/bin/env python3
"""로컬 원본만 빌드 디렉터리에 전개하고 단일 카탈로그를 만들어요."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from urllib.parse import urlparse

PREFIX = Path("assets/plugins/knowledge-work")
MAX_FILE_BYTES = 8 * 1024 * 1024


def safe_path(path: str) -> str:
    """원본 경로도 명시적인 상대 경로 규칙을 통과해야 해요."""
    if not path or path.startswith("/") or "\\" in path or any(ord(c) < 32 for c in path):
        raise ValueError(f"안전하지 않은 경로예요: {path!r}")
    if any(part in ("", ".", "..") for part in path.split("/")):
        raise ValueError(f"안전하지 않은 경로예요: {path!r}")
    return path


def local_domains(root: Path) -> list[Path]:
    """marketplace 원격 소스를 가져오지 않고 실제 로컬 매니페스트를 찾아요."""
    manifests = sorted(list(root.glob("*/.claude-plugin/plugin.json")) +
                       list(root.glob("partner-built/*/.claude-plugin/plugin.json")))
    domains = [p.parent.parent for p in manifests]
    if not domains:
        raise ValueError("로컬 플러그인 매니페스트가 없어요.")
    return domains


def asset_path(path: str) -> str:
    """Android 자산이 숨김 경로를 버리므로 점으로 시작하는 조각만 바꿔요."""
    return "/".join("dot-" + part[1:] if part.startswith(".") else part for part in path.split("/"))


def stage(root: Path, output: Path) -> dict:
    root = root.resolve(strict=True)
    output = output.absolute()
    resolved_output = output.resolve()
    allowed_roots = (root / "build", root / "logent-plugin/build")
    if output != resolved_output or not any(base in resolved_output.parents for base in allowed_roots):
        raise ValueError("출력은 저장소 build/ 아래의 하위 디렉터리여야 해요.")
    domains = local_domains(root)
    catalog = {"schema": 1, "domains": [], "files": [], "connectors": []}
    ids: set[str] = set()
    sources: list[tuple[Path, str, str]] = []
    for domain in domains:
        if domain.is_symlink() or any(p.is_symlink() for p in domain.parents if p != root and root in p.parents):
            raise ValueError(f"심볼릭 링크 도메인은 배포하지 않아요: {domain}")
        rel = domain.relative_to(root).as_posix()
        domain_id = domain.name
        if domain_id in ids or not all(c in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in domain_id):
            raise ValueError(f"중복되거나 잘못된 도메인이에요: {domain_id}")
        ids.add(domain_id)
        record = {"id": domain_id, "path": rel, "skills": [], "commands": []}
        for path in sorted(domain.rglob("*")):
            relative = safe_path(path.relative_to(root).as_posix())
            # 디렉터리 심볼릭 링크도 원본 경계를 벗어날 수 있어요.
            if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root and root in p.parents):
                raise ValueError(f"심볼릭 링크는 배포하지 않아요: {relative}")
            if not path.is_file():
                continue
            if not path.resolve().is_relative_to(root):
                raise ValueError(f"원본 경계를 벗어났어요: {relative}")
            inner = path.relative_to(domain).as_posix()
            kind = "skill" if inner.startswith("skills/") and path.name == "SKILL.md" else (
                "command" if inner.startswith("commands/") and path.suffix == ".md" else "support")
            if kind == "skill":
                record["skills"].append(relative)
            elif kind == "command":
                record["commands"].append(relative)
            sources.append((path, domain_id, kind))
        catalog["domains"].append(record)
        config = domain / ".mcp.json"
        if config.is_file():
            servers = json.loads(config.read_text(encoding="utf-8"))["mcpServers"]
            for name, server in sorted(servers.items()):
                url = server.get("url", "")
                parsed = urlparse(url) if isinstance(url, str) else urlparse("")
                supported = (server.get("type") in ("http", "sse") and parsed.scheme == "https"
                             and bool(parsed.hostname) and not parsed.username and not parsed.password)
                catalog["connectors"].append({
                    "domain": domain_id, "name": name, "path": f"{rel}/.mcp.json",
                    "transport": server.get("type", "stdio" if "command" in server else "unknown"),
                    "url": url if supported else "", "supported": supported,
                    "reason": "수동 HTTPS 연결 제안이에요. 인증과 접근 권한을 직접 확인해요." if supported else
                              "빈 URL·비 HTTPS·stdio는 자동 연결하거나 실행하지 않아요. 원본 설정을 확인해요.",
                })
    sources += [(root / "LICENSE", "", "attribution"),
                (root / ".claude-plugin/marketplace.json", "", "marketplace")]
    staged: list[tuple[str, bytes]] = []
    for source, domain_id, kind in sorted(sources, key=lambda item: item[0].as_posix()):
        relative = safe_path(source.relative_to(root).as_posix())
        if source.is_symlink() or not source.resolve().is_relative_to(root):
            raise ValueError(f"안전하지 않은 원본이에요: {relative}")
        content = source.read_bytes()
        if len(content) > MAX_FILE_BYTES:
            raise ValueError(f"파일 크기 한도를 넘었어요: {relative}")
        content.decode("utf-8", errors="strict")
        catalog["files"].append({"path": relative, "asset": asset_path(relative), "domain": domain_id, "kind": kind,
                                 "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
        staged.append((asset_path(relative), content))
    # 모든 검증을 마친 뒤 생성 결과만 교체해요.
    if len({relative for relative, _ in staged}) != len(staged):
        raise ValueError("물리 자산 경로가 중복돼요.")
    if output.exists():
        shutil.rmtree(output)
    assets = output / PREFIX
    assets.mkdir(parents=True)
    for relative, content in staged:
        target = assets / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    (assets / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    kotlin = output / "kotlin/com/sleepysoong/logent/knowledgework/KnowledgeDomains.kt"
    kotlin.parent.mkdir(parents=True, exist_ok=True)
    entries = "\n".join(f'    "{d["id"]}" to "{d["path"]}",' for d in catalog["domains"])
    kotlin.write_text("package com.sleepysoong.logent.knowledgework\n\n"
                      "// 로컬 원본 매니페스트에서 빌드할 때 생성해요. 직접 수정하지 않아요.\n"
                      f"internal val KNOWLEDGE_DOMAINS: List<Pair<String, String>> = listOf(\n{entries}\n)\n", encoding="utf-8")
    return catalog


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    catalog = stage(args.root, args.output)
    print(json.dumps({"domains": len(catalog["domains"]), "skills": sum(len(d["skills"]) for d in catalog["domains"]),
                      "commands": sum(len(d["commands"]) for d in catalog["domains"]), "files": len(catalog["files"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
