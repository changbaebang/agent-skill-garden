import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "private_skill_init.py")


def run(alias, priv, pub):
    return subprocess.run([sys.executable, SCRIPT, alias, "--private-root", priv, "--skills-root", pub],
                          capture_output=True, text=True)


class ScaffoldTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.priv = os.path.join(self.tmp.name, "private")
        self.pub = os.path.join(self.tmp.name, "skills")

    def tearDown(self):
        self.tmp.cleanup()

    def test_creates_hash_dir_and_symlink(self):
        r = run("My_Skill Name", self.priv, self.pub)
        self.assertEqual(r.returncode, 0, r.stderr)
        link = os.path.join(self.pub, "my-skill-name")
        self.assertTrue(os.path.islink(link))
        target = os.readlink(link)
        self.assertRegex(os.path.basename(target), r"^[0-9a-f]{32}$")
        self.assertTrue(os.path.isfile(os.path.join(link, "SKILL.md")))

    def test_refuses_real_directory(self):
        os.makedirs(os.path.join(self.pub, "taken"))
        self.assertEqual(run("taken", self.priv, self.pub).returncode, 1)

    def test_refuses_existing_private_alias(self):
        run("again", self.priv, self.pub)
        self.assertEqual(run("again", self.priv, self.pub).returncode, 1)

    def test_invalid_alias(self):
        self.assertEqual(run("!!!", self.priv, self.pub).returncode, 1)

    def test_roots_required(self):
        env = {k: v for k, v in os.environ.items() if k not in ("PRIVATE_SKILLS_ROOT", "SKILLS_ROOT")}
        r = subprocess.run([sys.executable, SCRIPT, "x"], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
