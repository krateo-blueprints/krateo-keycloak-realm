#!/usr/bin/env python3
"""CI gate for users[]: every KeycloakUser the chart renders carries helm.sh/resource-policy: keep
(an uninstall or a feature-off must not delete a person's CR) and krateo.io/deletion-policy, renders
no credentials, and the chart default renders none (real addresses live only in private values).
A self-test strips `keep` from the render and requires the check to fail.
Usage: hack/check-users.py   (from the repo root; needs helm and pyyaml)
"""
import shutil, subprocess, sys, tempfile
from pathlib import Path
import yaml

CHART = Path("helm/krateo-keycloak-realm")
BASE = ["--set", "parentClient.redirectUris[0]=https://x/auth"]
USERS = ["--set-json", 'users=[{"username":"persona-a","email":"a@example.invalid","emailVerified":true},{"username":"persona-b","enabled":false}]']


def render(extra):
    work = Path(tempfile.mkdtemp(prefix="users-"))
    try:
        dst = work / "c"
        shutil.copytree(CHART, dst)
        cy = dst / "Chart.yaml"
        cy.write_text(cy.read_text().replace("CHART_VERSION", "0.0.0-ci"))
        p = subprocess.run(["helm", "template", "r", str(dst), *BASE, *extra], capture_output=True, text=True)
        if p.returncode != 0:
            sys.exit(f"::error::render failed: {p.stderr.strip()[:400]}")
        return [d for d in yaml.safe_load_all(p.stdout) if d]
    finally:
        shutil.rmtree(work, ignore_errors=True)


def problems(docs):
    out = []
    users = [d for d in docs if d["kind"] == "KeycloakUser"]
    for d in users:
        a = d["metadata"].get("annotations") or {}
        n = d["metadata"]["name"]
        if a.get("helm.sh/resource-policy") != "keep":
            out.append(f"{n} lacks helm.sh/resource-policy: keep (an uninstall would delete the person's CR)")
        if "krateo.io/deletion-policy" not in a:
            out.append(f"{n} lacks krateo.io/deletion-policy")
        if "credentials" in d["spec"]:
            out.append(f"{n} renders credentials: the chart must never carry a password")
    return users, out


errors = []
users, errs = problems(render(USERS))
errors += errs
if len(users) != 2:
    errors.append(f"expected 2 KeycloakUsers from 2 users[] entries, rendered {len(users)}")
if [d for d in render([]) if d["kind"] == "KeycloakUser"]:
    errors.append("the chart default renders KeycloakUsers: users[] must default to empty")
mutant = [dict(d, metadata=dict(d["metadata"], annotations={k: v for k, v in (d["metadata"].get("annotations") or {}).items() if k != "helm.sh/resource-policy"})) if d["kind"] == "KeycloakUser" else d for d in render(USERS)]
if not problems(mutant)[1]:
    errors.append("self-test: stripping `keep` was NOT detected")
print(f"Checked {len(users)} KeycloakUser(s): keep, deletion-policy, no credentials; default renders none.")
for e in errors:
    print(f"::error::{e}")
sys.exit(1 if errors else 0)
