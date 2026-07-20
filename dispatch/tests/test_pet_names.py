from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "dispatch-create.zsh"


class DispatchPetNameTests(unittest.TestCase):
    def test_collision_selects_a_new_pair_without_a_numeric_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            dispatch_home = root / "dispatch"
            fake_bin = root / "bin"
            repo.mkdir()
            fake_bin.mkdir()
            fake_date = fake_bin / "date"
            fake_date.write_text("#!/bin/sh\nprintf '%s\\n' 2026-07-20T15:00:00Z\n", encoding="utf-8")
            fake_date.chmod(0o755)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
            (repo / "README.md").write_text("test\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-qm", "test"], check=True)
            env = {
                **os.environ,
                "CODEX_DISPATCH_HOME": str(dispatch_home),
                "PATH": f"{fake_bin}:{os.environ['PATH']}",
            }
            command = [str(SCRIPT), "--repo", str(repo), "--task", "same task"]
            first = subprocess.run(command, check=True, capture_output=True, text=True, env=env)
            second = subprocess.run(command, check=True, capture_output=True, text=True, env=env)

            first_name = re.search(r"^name=(.+)$", first.stdout, re.MULTILINE).group(1)
            second_name = re.search(r"^name=(.+)$", second.stdout, re.MULTILINE).group(1)
            self.assertNotEqual(first_name, second_name)
            self.assertRegex(first_name, r"^[a-z]+-[a-z]+$")
            self.assertRegex(second_name, r"^[a-z]+-[a-z]+$")

            worker_dir = dispatch_home / "workers" / first_name
            (worker_dir / "agent_id").write_text(
                "019f8016-c8e5-7ae0-8935-6e332c13f90a\n",
                encoding="utf-8",
            )
            subprocess.run(
                [
                    str(SCRIPT.parent / "dispatch-state.zsh"),
                    "--worker",
                    first_name,
                    "--status",
                    "running",
                    "--display-name",
                    f"scythe/worker/{first_name}",
                    "--message",
                    "named",
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            state = json.loads((worker_dir / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["agent_id"], "019f8016-c8e5-7ae0-8935-6e332c13f90a")
            self.assertEqual(state["display_name"], f"scythe/worker/{first_name}")


if __name__ == "__main__":
    unittest.main()
