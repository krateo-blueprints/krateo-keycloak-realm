#!/usr/bin/env python3
"""CI gate: every Keycloak resource the chart renders carries krateo.io/deletion-policy, and the
default is `orphan`, so an uninstall, prune or delete of this chart never deletes the realm (and with
it every user). A self-test flips the default to `delete` and requires the check to fail."""
import shutil, subprocess, sys, tempfile
from pathlib import Path
import yaml

CHART = Path("helm/krateo-keycloak-realm")

# Every optional client switched on, so the new objects are checked too (0.5.0).
ALL = ["--set", "identityLifecycle.enabled=true", "--set", "ideClient.enabled=true",
       "--set", "ideClient.audience=https://x/mcp", "--set", "clients[0].clientId=rp",
       "--set", "clients[0].redirectUris[0]=https://rp/cb"]


def render(extra=()):
    work = Path(tempfile.mkdtemp(prefix="delpol-"))
    try:
        dst = work / "c"
        shutil.copytree(CHART, dst)
        cy = dst / "Chart.yaml"
        cy.write_text(cy.read_text().replace("CHART_VERSION", "0.0.0-ci"))
        p = subprocess.run(["helm", "template", "r", str(dst), "--set", "parentClient.redirectUris[0]=https://x/auth", *extra],
                           capture_output=True, text=True)
        if p.returncode != 0:
            sys.exit(f"::error::render failed: {p.stderr.strip()[:400]}")
        return [d for d in yaml.safe_load_all(p.stdout) if d]
    finally:
        shutil.rmtree(work, ignore_errors=True)


def bad(docs):
    res = [d for d in docs if d["kind"].startswith("Keycloak") and not d["kind"].endswith("Configuration")]
    return res, [d["kind"] + "/" + d["metadata"]["name"] for d in res
                 if (d["metadata"].get("annotations") or {}).get("krateo.io/deletion-policy") != "orphan"]


res, b = bad(render(ALL))
errors = [f"{x} is not krateo.io/deletion-policy: orphan by default" for x in b]
if len(res) < 8:
    errors.append(f"expected >= 8 Keycloak resources (realm, 2 groups, user profile, portal + rp + identity-lifecycle + IDE clients, role mapping), rendered {len(res)}")
if not bad(render(["--set", "deletionPolicy=delete"]))[1]:
    errors.append("self-test: deletionPolicy=delete was NOT detected")
print(f"Checked {len(res)} Keycloak resource(s) for krateo.io/deletion-policy: orphan by default.")
for e in errors:
    print(f"::error::{e}")
sys.exit(1 if errors else 0)
