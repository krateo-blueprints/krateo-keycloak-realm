#!/usr/bin/env python3
"""CI gate: values.schema.json's userProfile.attributes[] accepts exactly the attribute shape keycloak-config-kog's
KeycloakUserProfile CRD declares, and every object in it is closed. The snapshot in hack/testdata is the CRD oasgen generated
from the released KOG on a cluster, not the KOG's OpenAPI source: it is the CRD that prunes, and oasgen types a `number` as an
integer there. (A bare `number` here would also become a string in the composition CRD core-provider generates.)

WHY. The chart passes each attribute to the KeycloakUserProfile CR as it is. A key the CRD does not declare is PRUNED
silently: a misspelt validator (`lenght`) passed the chart while `validations` was a bare object, and the attribute
then had no validation at all. A key the CRD declares and this schema does not is one the chart refuses for nothing.

Compared: property names, types, array items and enums; not descriptions. Self-test: five mutants must be refused."""
import copy, json, shutil, subprocess, sys, tempfile
from pathlib import Path

CHART = Path("helm/krateo-keycloak-realm")
KOG = json.loads(sorted(Path("hack/testdata").glob("keycloak-config-kog-*-keycloakuserprofile-crd-attribute.schema.json"))[-1].read_text())


def diff(kog, ours, at="attribute"):
    out = []
    if kog.get("type") != ours.get("type"):
        return [f"{at}: type {ours.get('type')!r}, the KOG's is {kog.get('type')!r}"]
    if kog.get("type") == "object":
        kp, op = kog.get("properties"), ours.get("properties")
        if kp is None:  # a map (annotations)
            if kog.get("additionalProperties") != ours.get("additionalProperties") or op is not None:
                out.append(f"{at}: not the KOG's map")
            return out
        if ours.get("additionalProperties") is not False:
            out.append(f"{at}: not closed (additionalProperties must be false)")
        out += [f"{at}.{k}: the KOG declares it, this schema does not" for k in sorted(set(kp) - set(op or {}))]
        out += [f"{at}.{k}: this schema accepts it, the KOG's CRD prunes it" for k in sorted(set(op or {}) - set(kp))]
        for k in sorted(set(kp) & set(op or {})):
            out += diff(kp[k], op[k], f"{at}.{k}")
    elif kog.get("type") == "array":
        out += diff(kog["items"], ours.get("items") or {}, at + "[]")
    elif kog.get("enum") != ours.get("enum"):
        out.append(f"{at}: enum {ours.get('enum')}, the KOG's is {kog.get('enum')}")
    return out


def attr(schema):
    return schema["properties"]["userProfile"]["properties"]["attributes"]["items"]


schema = json.loads((CHART / "values.schema.json").read_text())
bad = diff(KOG, attr(schema))
if bad:
    print("\n".join("::error::" + b for b in bad)); sys.exit(1)


def mutant(f):
    s = copy.deepcopy(schema); f(attr(s)); return diff(KOG, attr(s))


V = lambda a: a["properties"]["validations"]
for name, f in {"validations a bare object": lambda a: a["properties"].update(validations={"type": "object"}),
                "a validator dropped": lambda a: V(a)["properties"].pop("pattern"),
                "one the KOG lacks": lambda a: V(a)["properties"].update(lenght={"type": "object", "properties": {}, "additionalProperties": False}),
                "a bare number": lambda a: V(a)["properties"]["double"]["properties"].update(max={"type": "number"}),
                "a validator left open": lambda a: V(a)["properties"]["length"].pop("additionalProperties")}.items():
    if not mutant(f):
        sys.exit(f"::error::self-test: not caught: {name}")


def render(v):
    work = Path(tempfile.mkdtemp(prefix="userprofile-"))
    try:
        dst = work / "c"; shutil.copytree(CHART, dst)
        cy = dst / "Chart.yaml"; cy.write_text(cy.read_text().replace("CHART_VERSION", "0.0.0-ci"))
        vf = work / "v.json"
        vf.write_text(json.dumps({"parentClient": {"redirectUris": ["https://x/auth"]},
                                  "userProfile": {"attributes": [{"name": "a", "validations": v}]}}))
        return subprocess.run(["helm", "template", "r", str(dst), "-f", str(vf)], capture_output=True, text=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)


p = render({"length": {"max": 36}, "pattern": {"pattern": "^a$", "error-message": "no"}})
if p.returncode or "max: 36" not in p.stdout:
    sys.exit("::error::a declared validator must render: " + p.stderr[:300])
for v in ({"lenght": {"max": 36}}, {"length": {"maximum": 36}}, {"length": {"max": "36"}}, {"double": {"max": 0.5}}):
    p = render(v)
    if p.returncode == 0 or "validations" not in p.stderr:
        sys.exit(f"::error::{v} must be refused by name (rc {p.returncode}): {p.stderr[:200]}")
print("userProfile attributes: the KOG's shape, closed; 5 mutants and 4 values refused, the control renders.")
