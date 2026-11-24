#!/usr/bin/env python3
"""CI gate: every chart renders with the values of its previous releases, as `helm upgrade
--reuse-values` gives them.

WHY. With --reuse-values Helm upgrades using the PREVIOUS release's values and does not apply the new
chart's values.yaml defaults. A template that reads a key added since then (e.g. 0.2.6's
`.Values.crdOwnershipBridge.enabled`) fails with a nil pointer, and the upgrade aborts.

WHAT. For each chart and each previous semver tag listed below, render the chart with its values.yaml
REPLACED by that tag's values.yaml (exactly the reuse-values shape), and require success. The render
with the chart's own defaults must produce the same kinds, so a defaulted key cannot silently switch a
feature off under reuse-values either.
SELF-TEST: a template reading a key absent from the old values must fail the render.
"""
import re, shutil, subprocess, sys, tempfile
from pathlib import Path
import yaml

CHARTS = ["helm/krateo-keycloak-realm"]  # each is rendered under every published release (the git tags)
SETS = {"helm/krateo-keycloak-realm": ["--set", "parentClient.redirectUris[0]=https://x/cb"]}


def render(chart, values_text, extra_template=None):
    work = Path(tempfile.mkdtemp(prefix="reuse-"))
    try:
        dst = work / "c"
        shutil.copytree(chart, dst)
        cy = dst / "Chart.yaml"
        cy.write_text(cy.read_text().replace("CHART_VERSION", "0.0.0-ci"))
        if values_text is not None:
            (dst / "values.yaml").write_text(values_text)
        if extra_template:
            (dst / "templates" / "zz-selftest.yaml").write_text(extra_template)
        p = subprocess.run(["helm", "template", "r", str(dst), "-n", "krateo-system", *SETS.get(chart, [])], capture_output=True, text=True)
        return p.returncode, p.stdout, p.stderr
    finally:
        shutil.rmtree(work, ignore_errors=True)


def kinds(out):
    return sorted((d["kind"], d["metadata"]["name"]) for d in yaml.safe_load_all(out) if d)


errors = []
# The templates' fallback defaults must be exactly values.yaml, or a reuse-values upgrade renders
# something a fresh install would not.
_v = yaml.safe_load(open("helm/krateo-keycloak-realm/values.yaml"))
_f = yaml.safe_load(open("helm/krateo-keycloak-realm/files/values.defaults.yaml"))
if _v != _f:
    errors.append("files/values.defaults.yaml differs from values.yaml: keep them equal")
# Every published release, from the tags: a hand-kept list stopped at 0.3.2 while 0.6.3 was out, so upgrades from any release
# in between were never rendered (0.7.0's first guard refused 0.5.0 - 0.6.3's own default values).
published = sorted((t for t in subprocess.run(["git", "tag", "--list"], capture_output=True, text=True).stdout.split()
                    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", t)), key=lambda t: [int(x) for x in t.split(".")])
# 0.1.0 is the first release: without it the checkout has no tags, or not all of them (fetch-depth: 0 is needed)
if "0.1.0" not in published:
    errors.append("release tag 0.1.0 is not in this checkout (fetch-depth: 0 is needed): not every release would be checked")
for chart in CHARTS:
    rc, ref, err = render(chart, None)
    if rc != 0:
        errors.append(f"{chart}: does not render with its own defaults: {err.strip()[:300]}")
        continue
    for tag in published:
        old = subprocess.run(["git", "show", f"{tag}:{chart}/values.yaml"], capture_output=True, text=True)
        if old.returncode != 0:
            errors.append(f"{chart}: cannot read values.yaml at tag {tag}: {old.stderr.strip()[:200]}")
            continue
        sel = render(chart, old.stdout, "{{ if .Values.selfTestKeyAddedLater.enabled }}x{{ end }}\n")
        if sel[0] == 0:
            sys.exit("::error::self-test: a template reading an absent key rendered; the gate is broken")
        rc, out, err = render(chart, old.stdout)
        if rc != 0:
            errors.append(f"{chart}: `helm upgrade --reuse-values` from {tag} would fail: {err.strip()[:300]}")
        elif kinds(out) != kinds(ref):
            errors.append(f"{chart}: under {tag}'s values it renders {kinds(out)} instead of {kinds(ref)}")
for e in errors:
    print(f"::error::{e}")
if errors:
    sys.exit(1)
print(f"Checked: each chart renders, with the same objects, under its {len(published)} previous releases' values (--reuse-values).")
