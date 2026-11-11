---
type: Architecture
title: krateo-keycloak-realm — overview
description: Why the parent realm is a chart of KOG resources, and the three safety properties it guarantees: deletion protection, Configurations that outlive their resources, and Secret-sourced mail credentials.
resource: oci://ghcr.io/krateo-blueprints/charts/krateo-keycloak-realm
tags: [architecture, keycloak]
timestamp: 2026-11-11T00:00:00Z
---

# Overview

The chart renders, in the release namespace:

- one `<Kind>Configuration` per kind (realm, group, client) pointing at the bearer-token Secret
  keycloak-config-kog keeps fresh;
- a `KeycloakRealm`, a `KeycloakGroup` per entry of `groups`, and a `KeycloakClient` for the portal.

Users and group memberships are deliberately **not** declared here: they belong to whoever runs the
joiner flow (on Krateo, identity-lifecycle). Two writers on one user or membership fight forever.

Three properties are enforced by the templates and by CI gates in `hack/`:

1. **Deletion protection.** Every Keycloak resource carries `krateo.io/deletion-policy: orphan` by
   default: uninstalling, pruning or deleting a resource never deletes the realm (and every user in
   it). Set `deletionPolicy: delete` only to decommission.
2. **Configurations outlive their resources.** They carry `helm.sh/resource-policy: keep`, because
   `helm uninstall` deletes everything in one pass and a resource whose finalizer can no longer
   authenticate would never finish deleting.
3. **No credential in a resource.** SMTP credentials come from a Secret through
   `smtpCredentialsRef`; the realm resource names the Secret's keys, never their values.
