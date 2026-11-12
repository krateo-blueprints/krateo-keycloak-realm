#!/usr/bin/env python3
"""CI gate: every user event type the chart enables is a real Keycloak EventType.

WHY. Keycloak stores `enabledEventTypes` as plain strings and accepts any name without complaint. A
name that is not an EventType records nothing, and querying events by it fails with HTTP 500 ("No
enum constant EventType..."). realm 0.2.0/0.3.0 shipped two such names (SEND_EXECUTE_ACTIONS,
SEND_ERROR), so the realm recorded no user events at all, and nothing reported it.

WHAT. The rendered KeycloakRealm's spec.enabledEventTypes, for the default values and for every
values file under examples/, must be a subset of hack/testdata/keycloak-<version>-event-types.json:
the `enums.eventType` list from the Admin API's /admin/serverinfo of that Keycloak release, the
release the keycloak chart ships. Deprecated types are flagged too, so the list keeps current names.

SELF-TEST. A mutant render with an unknown type must fail and a control render must pass.

DUPLICATES. Keycloak keeps types and listeners as sets and the KOG compares them as sets, so a
duplicate never converges. The chart refuses one at render (kr.check); this gate requires that a
duplicate in either list fails the render with a message naming the key and the value.
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path
import yaml

CHART = Path("helm/krateo-keycloak-realm")
PINNED = sorted(Path("hack/testdata").glob("keycloak-*-event-types.json"))
DEPRECATED = {"UPDATE_PASSWORD", "UPDATE_PASSWORD_ERROR", "UPDATE_TOTP", "UPDATE_TOTP_ERROR",
              "REMOVE_TOTP", "REMOVE_TOTP_ERROR", "VALIDATE_ACCESS_TOKEN", "VALIDATE_ACCESS_TOKEN_ERROR"}


def render_raw(extra=()):
    work = Path(tempfile.mkdtemp(prefix="evtypes-"))
    try:
        dst = work / "c"
        shutil.copytree(CHART, dst)
        cy = dst / "Chart.yaml"
        cy.write_text(cy.read_text().replace("CHART_VERSION", "0.0.0-ci"))
        return subprocess.run(["helm", "template", "r", str(dst), "--set", "parentClient.redirectUris[0]=https://x/auth", *extra],
                              capture_output=True, text=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def render(extra=()):
    work = Path(tempfile.mkdtemp(prefix="evtypes-"))
    try:
        dst = work / "c"
        shutil.copytree(CHART, dst)
        cy = dst / "Chart.yaml"
        cy.write_text(cy.read_text().replace("CHART_VERSION", "0.0.0-ci"))
        p = subprocess.run(["helm", "template", "r", str(dst), "--set", "parentClient.redirectUris[0]=https://x/auth", *extra],
                           capture_output=True, text=True)
        if p.returncode != 0:
            sys.exit(f"::error::render failed: {p.stderr.strip()[:400]}")
        realms = [d for d in yaml.safe_load_all(p.stdout) if d and d.get("kind") == "KeycloakRealm"]
        return realms[0]["spec"].get("enabledEventTypes", []) if realms else []
    finally:
        shutil.rmtree(work, ignore_errors=True)


def problems(types, valid):
    return [f"{t} is not a Keycloak EventType" for t in types if t not in valid] + \
           [f"{t} is deprecated in Keycloak 26 (use UPDATE_CREDENTIAL / REMOVE_CREDENTIAL)" for t in types if t in DEPRECATED]


if len(PINNED) != 1:
    sys.exit(f"::error::expected exactly one hack/testdata/keycloak-*-event-types.json, found {[str(p) for p in PINNED]}")
valid = set(json.loads(PINNED[0].read_text()))

if not problems(render(["--set", "realm.events.types[0]=SEND_EXECUTE_ACTIONS"]), valid):
    sys.exit("::error::self-test: an unknown event type passed the check; the gate is broken")
if problems(["LOGIN", "UPDATE_CREDENTIAL"], valid):
    sys.exit("::error::self-test: valid event types failed the check; the gate is broken")

errors, checked = [], 0
for key, dup in (("types", "LOGIN"), ("listeners", "jboss-logging")):
    p = render_raw(["--set", f"realm.events.{key}={{{dup},{dup}}}"])
    want = f'realm.events.{key}: "{dup}" is listed twice'
    if p.returncode == 0 or want not in p.stderr:
        errors.append(f"a duplicate in realm.events.{key} must fail the render with `{want}`, got rc={p.returncode}: {p.stderr.strip()[:200]}")
for extra in [()] + [("-f", str(f)) for f in sorted(Path("examples").glob("*/values.yaml"))]:
    types = render(extra)
    checked += 1
    errors += [f"{' '.join(extra) or 'default values'}: {e}" for e in problems(types, valid)]
for e in errors:
    print(f"::error::{e}")
if errors:
    sys.exit(1)
print(f"Checked enabledEventTypes in {checked} render(s) against {PINNED[0].name} ({len(valid)} types).")
