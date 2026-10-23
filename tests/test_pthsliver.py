import tempfile
import unittest
from pathlib import Path

import pthsliver


class BuildLineTests(unittest.TestCase):
    def test_all_generated_lines_are_valid_python(self):
        lines = (
            pthsliver.build_windows_line(r"C:\Lab\agent.exe"),
            pthsliver.build_posix_line("/tmp/agent"),
            pthsliver.build_macos_line("/tmp/agent"),
            pthsliver.build_macos_line("/tmp/agent", remove_quarantine=True),
        )
        for line in lines:
            with self.subTest(line=line):
                compile(line, "<generated>", "exec")
                self.assertTrue(line.startswith("import "))
                self.assertNotIn("\n", line)

    def test_windows_path_is_not_rewritten_by_host(self):
        path = r"C:\Program Files\Lab\agent.exe"
        self.assertIn(repr(path), pthsliver.build_windows_line(path))

    def test_quoted_macos_path_is_data_not_shell_syntax(self):
        path = "/tmp/lab agent's copy"
        line = pthsliver.build_macos_line(path, remove_quarantine=True)
        self.assertIn(repr(path), line)
        self.assertIn("'/usr/bin/xattr'", line)
        self.assertIn("'com.apple.quarantine'", line)
        self.assertNotIn("os.system", line)
        compile(line, "<generated>", "exec")

    def test_macos_quarantine_removal_is_opt_in(self):
        default_line = pthsliver.build_macos_line("/tmp/agent")
        enabled_line = pthsliver.build_macos_line(
            "/tmp/agent", remove_quarantine=True
        )
        self.assertNotIn("com.apple.quarantine", default_line)
        self.assertIn("com.apple.quarantine", enabled_line)


class GenerateTests(unittest.TestCase):
    def test_generate_writes_one_line_without_launching_it(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "test.pth"
            line = pthsliver.generate(
                "/tmp/harmless-demo", "linux", str(output), quiet=True
            )
            self.assertEqual(output.read_text(encoding="utf-8"), line + "\n")

    def test_generate_refuses_to_overwrite_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "test.pth"
            output.write_text("existing\n", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                pthsliver.generate(
                    "/tmp/harmless-demo", "linux", str(output), quiet=True
                )

    def test_target_path_must_be_absolute_for_selected_os(self):
        with tempfile.TemporaryDirectory() as directory:
            output = str(Path(directory) / "test.pth")
            with self.assertRaises(ValueError):
                pthsliver.generate("relative/path", "linux", output, quiet=True)
            with self.assertRaises(ValueError):
                pthsliver.generate("/unix/path", "windows", output, quiet=True)


if __name__ == "__main__":
    unittest.main()
