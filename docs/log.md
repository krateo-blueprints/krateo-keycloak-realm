---
type: Log
title: krateo-keycloak-realm — log
description: Curated history of krateo-keycloak-realm.
resource: oci://ghcr.io/krateo-blueprints/charts/krateo-keycloak-realm
tags: [log, history]
timestamp: 2026-11-11T00:00:00Z
---

# Log

## 2026-11-12 — 0.3.0: the realm's user profile

The chart now owns the realm's whole user profile through keycloak-config-kog 0.7.0's
`KeycloakUserProfile`: Keycloak 26's default profile verbatim
(`files/keycloak-26-default-user-profile.json`, read from a fresh realm on Keycloak 26.6.3), then
`userProfile.attributes`. The default attributes declare `krateo-access-request-uid` (admin view and
edit only, at most 36 characters), set by the joiner flow on the users it creates; before 0.3.0
Keycloak dropped it. Unmanaged attributes stay disabled. Needs keycloak-config-kog >= 0.7.0, or
`userProfile.enabled: false` on 0.6.0. Validated live (see keycloak-config-kog's 0.7.0 log entry):
users that existed before the profile still update, the attribute is invisible and read-only to the
user, and a console edit is reverted.

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
