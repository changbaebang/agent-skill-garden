import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "core" / "skills" / "local-dev-environment"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))
import profile_env  # noqa: E402

PROFILE = """[profile]
schema_version = 1
name = test
visibility = local

[integration.local-dev]
enabled = true
repo = {repo}
hostname = dev.example.test
cert_dir = {certs}
cert_var = SSL_CERT_PATH
key_var = SSL_KEY_PATH
port.web = 3002
port.my-app = 3003
extra_ports = 3010
"""


def run(cmd, env=None):
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


class LocalDevEnvironmentTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.repo = root / "repo"
        (self.repo / "apps" / "web").mkdir(parents=True)
        (self.repo / "apps" / "web" / "package.json").write_text(
            '{"scripts": {"dev": "x", "dev:qa": "x"}}')
        self.certs = root / "certs"
        self.profile = root / "profile.ini"
        self.profile.write_text(PROFILE.format(repo=self.repo, certs=self.certs))

    def env(self):
        out = run([sys.executable, str(SCRIPTS / "profile_env.py"), "--profile", str(self.profile)])
        self.assertEqual(out.returncode, 0, out.stderr)
        base = {k: v for k, v in os.environ.items() if not k.startswith("LOCAL_DEV_")}
        for line in out.stdout.splitlines():
            k, v = line[len("export "):].split("=", 1)
            base[k] = v.strip("'")
        return base

    def test_profile_values_and_ports(self):
        values = profile_env.load(str(self.profile))
        self.assertEqual(values["LOCAL_DEV_PORT_MY_APP"], "3003")
        self.assertEqual(values["LOCAL_DEV_PORTS"], "3002 3003 3010")
        self.assertEqual(values["LOCAL_DEV_APPS_DIR"], "apps")

    def test_missing_required_field_fails(self):
        self.profile.write_text("[integration.local-dev]\nrepo = /x\n")
        with self.assertRaises(SystemExit):
            profile_env.load(str(self.profile))

    def test_resolver_precedence(self):
        env = self.env()
        self.assertNotEqual(run(["bash", str(SCRIPTS / "resolve_cert.sh")], env).returncode, 0)
        self.certs.mkdir()
        (self.certs / "local-dev.pem").write_text("c")
        (self.certs / "local-dev-key.pem").write_text("k")
        out = run(["bash", str(SCRIPTS / "resolve_cert.sh")], env)
        self.assertIn("source=profile directory", out.stdout)
        other = Path(self.tmp.name) / "o.pem"
        other.write_text("c")
        other_key = Path(self.tmp.name) / "ok.pem"
        other_key.write_text("k")
        env["SSL_CERT_PATH"], env["SSL_KEY_PATH"] = str(other), str(other_key)
        out = run(["bash", str(SCRIPTS / "resolve_cert.sh")], env)
        self.assertIn("source=server variables", out.stdout)

    def test_run_dry_run_http_and_missing_script(self):
        env = self.env()
        out = run(["bash", str(SCRIPTS / "run_app.sh"), "web", "qa", "--http", "--dry-run"], env)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("pnpm -F web dev:qa", out.stdout)
        self.assertIn("http://dev.example.test:3002/", out.stdout)
        bad = run(["bash", str(SCRIPTS / "run_app.sh"), "web", "prod", "--http", "--dry-run"], env)
        self.assertNotEqual(bad.returncode, 0)

    def test_stop_requires_ports_and_reports_idle(self):
        env = self.env()
        env.pop("LOCAL_DEV_PORTS")
        self.assertEqual(run(["bash", str(SCRIPTS / "stop_dev_servers.sh")], env).returncode, 2)
        out = run(["bash", str(SCRIPTS / "stop_dev_servers.sh"), "--port", "59999", "--dry-run"], env)
        self.assertIn(":59999 idle", out.stdout)


if __name__ == "__main__":
    unittest.main()
