from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "isolate-dispatch.zsh"


class IsolatePetNameTests(unittest.TestCase):
    def test_collision_selects_a_new_pair_without_a_numeric_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            requests = root / "requests"
            completed = root / "completed"
            fake_bin = root / "bin"
            repo.mkdir()
            fake_bin.mkdir()
            fake_date = fake_bin / "date"
            fake_date.write_text("#!/bin/sh\nprintf '%s\\n' 20260720T150000\n", encoding="utf-8")
            fake_date.chmod(0o755)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
            (repo / "README.md").write_text("test\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-qm", "test"], check=True)
            env = {
                **os.environ,
                "CODEX_ISOLATE_REQUESTS_DIR": str(requests),
                "CODEX_ISOLATE_COMPLETED_DIR": str(completed),
                "PATH": f"{fake_bin}:{os.environ['PATH']}",
            }
            command = [str(SCRIPT), "--repo", str(repo), "--task", "same task"]
            first = subprocess.run(command, check=True, capture_output=True, text=True, env=env)
            second = subprocess.run(command, check=True, capture_output=True, text=True, env=env)

            first_name = re.search(r"^work_id=(.+)$", first.stdout, re.MULTILINE).group(1)
            second_name = re.search(r"^work_id=(.+)$", second.stdout, re.MULTILINE).group(1)
            self.assertNotEqual(first_name, second_name)
            self.assertRegex(first_name, r"^[a-z]+-[a-z]+$")
            self.assertRegex(second_name, r"^[a-z]+-[a-z]+$")


if __name__ == "__main__":
    unittest.main()
