package com.sleepysoong.logent.knowledgework

import com.sleepysoong.logent.plugin.PluginHost

/** 호스트가 검증한 아카이브에서도 카탈로그에 허용된 파일만 전개해요. */
internal suspend fun prepare(host: PluginHost, catalog: KnowledgeCatalog, domain: String): String {
    catalog.domain(domain)
    val files = catalog.files.filter { it.domain == domain }
    require(files.isNotEmpty()) { "전개할 파일이 없어요." }
    val archive = host.contentArchive(ASSET_PREFIX.removeSuffix("/")).getOrThrow()
    require(archive.isNotBlank() && archive.none { it == '\u0000' || it == '\n' || it == '\r' }) { "아카이브 경로가 올바르지 않아요." }
    val command = "python3 - ${shellQuote(archive)} ${shellQuote(domain)} ${shellQuote(catalog.digest)} <<'LOGENT_KNOWLEDGE_PREPARE'\n" +
        PREPARE_PYTHON + "\nLOGENT_KNOWLEDGE_PREPARE"
    val result = host.shell(command, 120).getOrThrow()
    require(result.success && !result.truncated) {
        "파일을 전개하지 못했어요. Termux의 python3, 저장 공간, 기존 파일·심볼릭 링크 여부를 확인해 주세요. " + result.output.take(1000)
    }
    return "요청한 $domain 도메인 원본 ${files.size}개를 Termux 홈의 .logent/knowledge-work/ 아래 원본 경로로 전개했어요. 스크립트 실행·의존성 설치·권한 상승은 하지 않았어요.\n${result.output.take(1000)}"
}

internal fun shellQuote(value: String): String = "'" + value.replace("'", "'\"'\"'") + "'"

// 이 어댑터는 원본 스크립트를 실행하지 않아요. 경로별 dir_fd와 O_NOFOLLOW로 전개 경계를 고정해요.
internal val PREPARE_PYTHON = """
import hashlib
import json
import os
import stat
import sys
import zipfile

PREFIX = "assets/plugins/knowledge-work/"
MAX_FILE = 8 * 1024 * 1024
opened = []
created = []
created_dirs = []

def safe_parts(path):
    parts = path.split("/")
    if not path or path.startswith("/") or "\\" in path or any(ord(c) < 32 or ord(c) == 127 for c in path):
        raise ValueError("안전하지 않은 경로예요.")
    if any(p in ("", ".", "..") for p in parts):
        raise ValueError("경로 이동은 허용하지 않아요.")
    return parts

def directory(parent, name):
    try:
        os.mkdir(name, 0o700, dir_fd=parent)
        created_dirs.append((parent, name))
    except FileExistsError:
        pass
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    opened.append(fd)
    return fd

try:
    payloads = []
    with zipfile.ZipFile(sys.argv[1]) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("중복 아카이브 항목은 허용하지 않아요.")
        catalog_info = archive.getinfo(PREFIX + "catalog.json")
        if catalog_info.file_size > 2 * 1024 * 1024 or stat.S_ISLNK(catalog_info.external_attr >> 16):
            raise ValueError("카탈로그 형식이나 크기가 맞지 않아요.")
        catalog_bytes = archive.read(catalog_info)
        if hashlib.sha256(catalog_bytes).hexdigest() != sys.argv[3]:
            raise ValueError("호스트와 아카이브의 카탈로그가 달라요.")
        catalog = json.loads(catalog_bytes.decode("utf-8", errors="strict"))
        entries = [entry for entry in catalog["files"] if entry["domain"] == sys.argv[2]]
        if not entries or len(entries) > 10000:
            raise ValueError("파일 목록이 올바르지 않아요.")
        for entry in entries:
            parts = safe_parts(entry["path"])
            asset = entry.get("asset", entry["path"])
            info = archive.getinfo(PREFIX + asset)
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode) or info.is_dir() or info.file_size != entry["bytes"] or info.file_size > MAX_FILE:
                raise ValueError("원본 파일 형식이나 크기가 맞지 않아요.")
            with archive.open(info) as source:
                data = source.read(MAX_FILE + 1)
            if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise ValueError("원본 파일 무결성이 맞지 않아요.")
            data.decode("utf-8", errors="strict")
            payloads.append((parts, data))
    home = os.environ.get("HOME", "")
    if not home.startswith("/"):
        raise ValueError("Termux 홈 경로가 올바르지 않아요.")
    # 홈 경로의 중간 구성요소도 심볼릭 링크를 따라가지 않아요.
    home_fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    opened.append(home_fd)
    for part in home.split("/"):
        if part:
            home_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=home_fd)
            opened.append(home_fd)
    root = directory(directory(home_fd, ".logent"), "knowledge-work")
    targets = []
    directories = {(): root}
    for parts, data in payloads:
        parent = root
        for index, part in enumerate(parts[:-1]):
            key = tuple(parts[:index + 1])
            if key not in directories:
                directories[key] = directory(parent, part)
            parent = directories[key]
        try:
            os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError("기존 파일이나 링크를 덮어쓰지 않아요.")
        targets.append((parent, parts[-1], data))
    for parent, name, data in targets:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        created.append((parent, name))
        with os.fdopen(fd, "wb") as target:
            target.write(data)
    print("파일 " + str(len(created)) + "개를 전개했어요. 기존 파일은 바꾸지 않았어요.")
except Exception as error:
    for parent, name in reversed(created):
        try:
            os.unlink(name, dir_fd=parent)
        except OSError:
            pass
    for parent, name in reversed(created_dirs):
        try:
            os.rmdir(name, dir_fd=parent)
        except OSError:
            pass
    print("전개 오류예요: " + str(error)[:500], file=sys.stderr)
    sys.exit(1)
finally:
    for fd in reversed(opened):
        os.close(fd)
""".trimIndent()
