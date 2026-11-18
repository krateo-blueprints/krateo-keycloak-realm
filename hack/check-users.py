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
USERS = ["--set-json", 'users=[{"username":"ada","name":"persona-a","email":"ada@example.invalid","emailVerified":true},{"username":"bob","enabled":false}]']


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
names = sorted(d["metadata"]["name"] for d in users)
if names != ["krateo-bob", "persona-a"]:
    errors.append(f"object names {names}: an explicit `name` must be used verbatim (adoption), else <realm>-<username>")
if len(users) != 2:
    errors.append(f"expected 2 KeycloakUsers from 2 users[] entries, rendered {len(users)}")
if [d for d in render([]) if d["kind"] == "KeycloakUser"]:
    errors.append("the chart default renders KeycloakUsers: users[] must default to empty")
mutant = [dict(d, metadata=dict(d["metadata"], annotations={k: v for k, v in (d["metadata"].get("annotations") or {}).items() if k != "helm.sh/resource-policy"})) if d["kind"] == "KeycloakUser" else d for d in render(USERS)]
if not problems(mutant)[1]:
    errors.append("self-test: stripping `keep` was NOT detected")
# The users[].username length bounds must equal the realm user profile's username validation, which Keycloak
# enforces at create (a 1-char username was refused with a 400 on a live cluster, 2026-11-18). One source of truth:
# the chart's own copy of Keycloak's default user profile. Plus a render-time negative: 2 chars must be refused.
import json as _json
_prof = _json.load(open(CHART / "files" / "keycloak-26-default-user-profile.json"))
_len = [a for a in _prof["attributes"] if a["name"] == "username"][0]["validations"]["length"]
_sch = _json.load(open(CHART / "values.schema.json"))["properties"]["users"]["items"]["properties"]["username"]
if (_sch.get("minLength"), _sch.get("maxLength")) != (int(_len["min"]), int(_len["max"])):
    errors.append("users[].username minLength/maxLength %s/%s != user profile username length %s/%s"
                  % (_sch.get("minLength"), _sch.get("maxLength"), _len["min"], _len["max"]))
_w = Path(tempfile.mkdtemp(prefix="users-neg-"))
try:
    shutil.copytree(CHART, _w / "c"); _cy = _w / "c" / "Chart.yaml"; _cy.write_text(_cy.read_text().replace("CHART_VERSION", "0.0.0-ci"))
    _p = subprocess.run(["helm", "template", "r", str(_w / "c"), *BASE, "--set-json", 'users=[{"username":"ab"}]'], capture_output=True, text=True)
    if _p.returncode == 0:
        errors.append("a 2-character username rendered: the realm user profile (min %s) would refuse it at create" % _len["min"])
    elif "username" not in _p.stderr or ("minLength" not in _p.stderr and "greater than or equal" not in _p.stderr):
        errors.append("a 2-character username was refused, but not by the length rule: " + _p.stderr.strip()[:200])
finally:
    shutil.rmtree(_w, ignore_errors=True)
# The rendered KeycloakUserConfiguration must carry configuration.query.findby.exact: true. Without it the KOG's user
# findby reads only Keycloak's first page of 100 users and strands a user sorting beyond it (measured 2026-11-18).
_ucfg = [d for d in render([]) if d["kind"] == "KeycloakUserConfiguration"]
if len(_ucfg) != 1 or ((_ucfg[0].get("spec") or {}).get("configuration") or {}).get("query", {}).get("findby", {}).get("exact") is not True:
    errors.append("KeycloakUserConfiguration must render configuration.query.findby.exact: true (the KOG user findby's exact match)")
print(f"Checked {len(users)} KeycloakUser(s): keep, deletion-policy, no credentials; default renders none.")
for e in errors:
    print(f"::error::{e}")
sys.exit(1 if errors else 0)
