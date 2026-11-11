---
type: Log
title: krateo-keycloak-realm — log
description: Curated history of krateo-keycloak-realm.
resource: oci://ghcr.io/krateo-blueprints/charts/krateo-keycloak-realm
tags: [log, history]
timestamp: 2026-11-11T00:00:00Z
---

# Log

## 2026-11-11 — 0.2.0

Renders authn's `OIDCConfig` from the realm's own client and groups (one source for issuer, client id,
redirect URI and allowed groups), only where authn's API exists, so the portal gets its Keycloak
sign-in. `krateo:` group names are refused (reserved by authn). Validated on GKE end to end through a
CompositionDefinition: a PKCE sign-in admitted a `tenants` member (200) and refused a user in no
allowed group (403). Also in 0.1.x: deletion protection (`orphan`) on every Keycloak resource.

## 2026-11-11 — 0.1.0

First release. Validated live on disposable GKE clusters against keycloak-operator 0.2.4, keycloak
0.2.5 (Keycloak 26.6.3) and keycloak-config-kog 0.6.0 on rest-dynamic-controller 0.56.0 and 0.59.0:
realm, groups and portal client reconcile; a real set-password email is delivered in password mode
and in token (XOAUTH2) mode; uninstall then reinstall completes (the Configurations are kept);
deleting the realm resource with the default policy leaves the realm in Keycloak.
