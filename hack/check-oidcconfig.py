#!/usr/bin/env python3
"""CI gate: the authn OIDCConfig this chart renders is valid against authn's CRD, its fields are all
declared there (an undeclared field would be pruned silently by the apiserver), and it agrees with
the client and groups it is derived from. Schema snapshot: hack/testdata (authn-crds 0.41.0).

Also checks the gate: without the OIDCConfig API the object is not rendered, so a cluster without
authn can still install the realm. Self-test: a mutant with an undeclared field must be refused."""
import json, shutil, subprocess, sys, tempfile, copy
from pathlib import Path
import yaml, jsonschema

CHART = Path("helm/krateo-keycloak-realm")
SCHEMA = json.loads(Path("hack/testdata/authn-crds-0.41.0-oidcconfig.schema.json").read_text())
API = "oidc.authn.krateo.io/v1alpha1/OIDCConfig"
VALS = ["--set", "parentClient.redirectUris[0]=https://cmp.example.com/auth?kind=oidc",
        "--set", "oidcConfig.keycloakUrl=https://keycloak.example.com/"]


def closed(s):
    """Make every object schema refuse undeclared properties (what pruning would silently drop)."""
    s = copy.deepcopy(s)
    def walk(n):
        if isinstance(n, dict):
            if n.get("type") == "object" and "properties" in n and not n.get("x-kubernetes-preserve-unknown-fields"):
                n.setdefault("additionalProperties", False)
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(s)
    return s


def render(extra):
    work = Path(tempfile.mkdtemp(prefix="oidccfg-"))
    try:
        dst = work / "c"
        shutil.copytree(CHART, dst)
        cy = dst / "Chart.yaml"
        cy.write_text(cy.read_text().replace("CHART_VERSION", "0.0.0-ci"))
        p = subprocess.run(["helm", "template", "r", str(dst), "-n", "krateo-system", *VALS, *extra], capture_output=True, text=True)
        if p.returncode != 0:
            sys.exit(f"::error::render failed: {p.stderr.strip()[:400]}")
        return [d for d in yaml.safe_load_all(p.stdout) if d]
    finally:
        shutil.rmtree(work, ignore_errors=True)


errors = []
strict = closed(SCHEMA)
docs = render(["--api-versions", API])
oc = [d for d in docs if d["kind"] == "OIDCConfig"]
client = [d for d in docs if d["kind"] == "KeycloakClient"]
groups = [d["spec"]["name"] for d in docs if d["kind"] == "KeycloakGroup"]
if len(oc) != 1:
    errors.append(f"expected exactly one OIDCConfig with the API present, rendered {len(oc)}")
else:
    o = oc[0]
    try:
        jsonschema.validate(o, strict)
    except jsonschema.ValidationError as e:
        errors.append(f"OIDCConfig invalid against authn-crds 0.41.0 (or carries an undeclared field): {e.message}")
    s = o["spec"]
    c = client[0]["spec"]
    if o["metadata"]["namespace"] != "krateo-system":
        errors.append("OIDCConfig is not in the release namespace")
    if s["clientID"] != c["clientId"]:
        errors.append("OIDCConfig clientID differs from the client's clientId")
    if s["redirectURI"] != c["redirectUris"][0]:
        errors.append("OIDCConfig redirectURI differs from the client's redirect URI")
    if sorted(s.get("allowedGroups", [])) != sorted(groups):
        errors.append("OIDCConfig allowedGroups differ from the realm groups")
    if s["issuer"] != "https://keycloak.example.com/realms/krateo" or not s["discoveryURL"].startswith(s["issuer"] + "/"):
        errors.append(f"issuer/discoveryURL not derived exactly (trailing slash trimmed): {s['issuer']} / {s['discoveryURL']}")
    if "clientSecret" in s:
        errors.append("OIDCConfig carries a clientSecret; the portal client is public (PKCE)")
    mutant = copy.deepcopy(o)
    mutant["spec"]["notAField"] = "x"
    try:
        jsonschema.validate(mutant, strict)
        errors.append("self-test: an undeclared field was NOT refused")
    except jsonschema.ValidationError:
        pass
if any(d["kind"] == "OIDCConfig" for d in render([])):
    errors.append("OIDCConfig rendered without the OIDCConfig API: a cluster without authn would fail the realm")
print(f"Checked the OIDCConfig against authn-crds 0.41.0, its derivation from the client and groups, and the API gate.")
for e in errors:
    print(f"::error::{e}")
sys.exit(1 if errors else 0)
