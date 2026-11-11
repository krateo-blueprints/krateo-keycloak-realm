#!/usr/bin/env python3
"""CI gate: every <Kind>Configuration the chart renders carries helm.sh/resource-policy: keep.

WHY. The realm/group/client CRs delete their Keycloak objects in a finalizer that authenticates
through the kind's Configuration. `helm uninstall` deletes all release objects at once, so without
`keep` the Configurations vanish first and every CR's delete fails forever (measured on GKE,
2026-11-11: "delete failed: keycloakrealmconfigurations ... keycloak-admin not found"), which also
blocks keycloak-config-kog's RestDefinitions from finalizing.

Renders the chart with the client enabled (so all three Configurations render) and checks each.
A self-test strips the annotation from the render and requires the check to fail.
Usage: hack/check-configurations-keep.py   (from the repo root; needs helm and pyyaml)
"""
import shutil, subprocess, sys, tempfile
from pathlib import Path
import yaml

CHART = Path("helm/krateo-keycloak-realm")


def render():
    work = Path(tempfile.mkdtemp(prefix="cfgkeep-"))
    try:
        dst = work / "c"
        shutil.copytree(CHART, dst)
        cy = dst / "Chart.yaml"
        cy.write_text(cy.read_text().replace("CHART_VERSION", "0.0.0-ci"))
        p = subprocess.run(["helm", "template", "r", str(dst), "--set", "parentClient.redirectUris[0]=https://x/auth"],
                           capture_output=True, text=True)
        if p.returncode != 0:
            sys.exit(f"::error::render failed: {p.stderr.strip()[:500]}")
        return [d for d in yaml.safe_load_all(p.stdout) if d]
    finally:
        shutil.rmtree(work, ignore_errors=True)


def missing(docs):
    cfgs = [d for d in docs if d["kind"].endswith("Configuration")]
    bad = [d["kind"] for d in cfgs if (d["metadata"].get("annotations") or {}).get("helm.sh/resource-policy") != "keep"]
    return cfgs, bad


docs = render()
cfgs, bad = missing(docs)
errors = []
if len(cfgs) < 3:
    errors.append(f"expected 3 Configurations (realm, group, client), rendered {len(cfgs)}")
errors += [f"{k} lacks helm.sh/resource-policy: keep (uninstall would deadlock the CRs' finalizers)" for k in bad]
mutant = [dict(d, metadata={k: v for k, v in d["metadata"].items() if k != "annotations"}) for d in docs]
if not missing(mutant)[1]:
    errors.append("self-test: stripping the annotation was NOT detected")
print(f"Checked {len(cfgs)} Configuration(s) for helm.sh/resource-policy: keep.")
for e in errors:
    print(f"::error::{e}")
sys.exit(1 if errors else 0)
