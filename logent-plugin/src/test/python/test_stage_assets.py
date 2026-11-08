"""원본 전개·참조 경계·명시적 Termux 전개 어댑터를 검사해요."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

REPO = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location("knowledge_stage", REPO / "logent/stage-assets.py")
STAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STAGE)
ADAPTER_SOURCE = (REPO / "logent-plugin/src/main/kotlin/com/sleepysoong/logent/knowledgework/KnowledgePrepare.kt").read_text(encoding="utf-8")
ADAPTER = ADAPTER_SOURCE.split('internal val PREPARE_PYTHON = """\n', 1)[1].split('\n""".trimIndent()', 1)[0]


class StageAssetsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.output = self.root / "logent-plugin/build/staged/pluginAssets"
        self.write("LICENSE", "원본 라이선스예요.\n")
        self.write(".claude-plugin/marketplace.json", json.dumps({"plugins": [
            {"name": "demo", "source": "./demo"},
            {"name": "external", "source": {"source": "github", "repo": "외부/원격"}},
        ]}))
        self.write("demo/.claude-plugin/plugin.json", '{"name":"demo"}')
        self.write("demo/skills/one/SKILL.md", "승인 후에만 진행해요.\n")
        self.write("demo/skills/one/nested/SKILL.md", "중첩 스킬이에요.\n")
        self.write("demo/commands/work.md", "명령 원문이에요.\n")
        self.write("demo/shared/reference.txt", "공유 참조예요.\n")
        self.write("demo/scripts/helper.py", "raise RuntimeError('실행하면 안 돼요.')\n")
        self.write("demo/.mcp.json", json.dumps({"mcpServers": {
            "https": {"type": "http", "url": "https://example.com/mcp"},
            "credential": {"type": "http", "url": "https://user:password@example.com/mcp"},
            "stdio": {"command": "npx", "args": ["금지예요"]},
        }}))
        self.write("partner-built/partner/.claude-plugin/plugin.json", '{"name":"partner"}')
        self.write("partner-built/partner/LICENSE", "파트너 라이선스예요.")

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_stages_all_originals_without_remote_sources(self):
        catalog = STAGE.stage(self.root, self.output)
        self.assertEqual(["demo", "partner"], [d["id"] for d in catalog["domains"]])
        self.assertEqual(2, len(catalog["domains"][0]["skills"]))
        self.assertEqual(1, len(catalog["domains"][0]["commands"]))
        original = {p.relative_to(self.root).as_posix() for d in (self.root / "demo", self.root / "partner-built/partner") for p in d.rglob("*") if p.is_file()}
        original.update(("LICENSE", ".claude-plugin/marketplace.json"))
        self.assertEqual(original, {f["path"] for f in catalog["files"]})
        assets = self.output / STAGE.PREFIX
        for file in catalog["files"]:
            data = (assets / file["asset"]).read_bytes()
            self.assertEqual((self.root / file["path"]).read_bytes(), data)
            self.assertEqual(file["sha256"], hashlib.sha256(data).hexdigest())
        self.assertFalse((assets / "external").exists())
        kotlin = self.output / "kotlin/com/sleepysoong/logent/knowledgework/KnowledgeDomains.kt"
        self.assertIn('"partner" to "partner-built/partner"', kotlin.read_text())

    def test_repeated_stage_is_deterministic_and_cleans_only_generated_files(self):
        first = STAGE.stage(self.root, self.output)
        stale = self.output / "stale.txt"
        stale.write_text("이전 결과예요.")
        second = STAGE.stage(self.root, self.output)
        self.assertEqual(first, second)
        self.assertFalse(stale.exists())
        self.assertTrue((self.root / "demo/scripts/helper.py").is_file())

    def test_mcp_only_offers_https_without_credentials(self):
        connectors = STAGE.stage(self.root, self.output)["connectors"]
        self.assertEqual(["https"], [c["name"] for c in connectors if c["supported"]])
        self.assertEqual(["", ""], [c["url"] for c in connectors if not c["supported"]])

    def test_rejects_outputs_that_could_delete_originals(self):
        for output in (self.root, self.root / "demo", self.root / "demo/build/stage", self.root / "build"):
            with self.subTest(output=output), self.assertRaises(ValueError):
                STAGE.stage(self.root, output)
        self.assertTrue((self.root / "demo/skills/one/SKILL.md").exists())

    def test_rejects_symlink_files_and_directories(self):
        link = self.root / "demo/shared/link"
        link.symlink_to(self.root / "LICENSE")
        with self.assertRaises(ValueError):
            STAGE.stage(self.root, self.output)
        link.unlink()
        link.symlink_to(self.root / "partner-built/partner", target_is_directory=True)
        with self.assertRaises(ValueError):
            STAGE.stage(self.root, self.output)

    def test_rejects_non_utf8_before_replacing_previous_output(self):
        STAGE.stage(self.root, self.output)
        before = (self.output / STAGE.PREFIX / "catalog.json").read_bytes()
        (self.root / "demo/binary.dat").write_bytes(b"\xff")
        with self.assertRaises(UnicodeDecodeError):
            STAGE.stage(self.root, self.output)
        self.assertEqual(before, (self.output / STAGE.PREFIX / "catalog.json").read_bytes())

    def test_rejects_path_traversal(self):
        for path in ("", "/etc/passwd", "../LICENSE", "demo/../LICENSE", "demo//file", "demo/./file", "demo\\file", "demo/\x00file"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                STAGE.safe_path(path)


class ExplicitPrepareTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        self.archive = self.root / "plugin.lpg"

    def package(self, files=None, symlink=False, duplicate=False, corrupt=False):
        files = files or {"demo/scripts/helper.py": b"raise RuntimeError('execute forbidden')\n", "demo/shared/ref.md": "승인 조건을 보존해요.".encode()}
        entries = [{"path": path, "domain": "demo", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} for path, data in files.items()]
        catalog = json.dumps({"schema": 1, "files": entries}, ensure_ascii=False).encode()
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("assets/plugins/knowledge-work/catalog.json", catalog)
            for index, (path, data) in enumerate(files.items()):
                info = zipfile.ZipInfo("assets/plugins/knowledge-work/" + path)
                if symlink and index == 0:
                    info.external_attr = 0o120777 << 16
                archive.writestr(info, b"wrong" if corrupt else data)
                if duplicate and index == 0:
                    archive.writestr(info, data)
        return hashlib.sha256(catalog).hexdigest()

    def run_prepare(self, digest):
        return subprocess.run([sys.executable, "-", str(self.archive), "demo", digest], input=ADAPTER,
                              text=True, capture_output=True, env={**os.environ, "HOME": str(self.home)}, timeout=20)

    def test_extracts_original_bytes_without_executing_and_never_overwrites(self):
        digest = self.package()
        result = self.run_prepare(digest)
        self.assertEqual(0, result.returncode, result.stderr)
        target = self.home / ".logent/knowledge-work/demo/scripts/helper.py"
        self.assertEqual(b"raise RuntimeError('execute forbidden')\n", target.read_bytes())
        target.write_bytes(b"user-owned")
        result = self.run_prepare(digest)
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(b"user-owned", target.read_bytes())

    def test_rejects_destination_symlinks_without_touching_target(self):
        digest = self.package()
        outside = self.root / "outside"
        outside.mkdir()
        (self.home / ".logent").symlink_to(outside, target_is_directory=True)
        result = self.run_prepare(digest)
        self.assertNotEqual(0, result.returncode)
        self.assertEqual([], list(outside.iterdir()))

    def test_rejects_malicious_zip_metadata_and_hash_mismatch(self):
        for options in ({"symlink": True}, {"duplicate": True}, {"corrupt": True}):
            with self.subTest(options=options):
                digest = self.package(**options)
                self.assertNotEqual(0, self.run_prepare(digest).returncode)
                self.assertFalse((self.home / ".logent").exists())
        self.package()
        self.assertNotEqual(0, self.run_prepare("0" * 64).returncode)

    def test_rejects_archive_traversal_and_preserves_outside(self):
        digest = self.package({"demo/../../escaped.md": b"bad"})
        self.assertNotEqual(0, self.run_prepare(digest).returncode)
        self.assertFalse((self.home / "escaped.md").exists())
        self.assertFalse((self.home / ".logent").exists())


if __name__ == "__main__":
    unittest.main()
