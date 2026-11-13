---
type: Usage
title: krateo-keycloak-realm — usage
description: Install the realm chart after keycloak-config-kog, choose password or token (XOAUTH2) mail, place the credentials Secret, rotate it, and verify mail end to end.
resource: oci://ghcr.io/krateo-blueprints/charts/krateo-keycloak-realm
tags: [usage, smtp, xoauth2]
timestamp: 2026-11-11T00:00:00Z
---

# Usage

## Prerequisites

keycloak-config-kog >= 0.7.1 and oasgen-provider >= 0.62.0 (Chart.yaml annotations `krateo.io/requires-*`), in the same namespace, its admin token Secret synced, and a Keycloak
>= 26.2 for token mail.

## User profile

Keycloak keeps one user profile per realm (the attributes users have, and who may see or change
each), and drops any attribute it does not declare. The chart renders the whole profile as one
`KeycloakUserProfile`: Keycloak 26's default profile, verbatim from
`files/keycloak-26-default-user-profile.json` (`username`, `email`, `firstName`, `lastName` and the
`user-metadata` group), followed by `userProfile.attributes`. Keeping the built-ins byte-identical to
Keycloak's default means users that existed before the chart managed the profile, such as migrated
accounts, meet exactly the rules they met before.

The default `attributes` declare `krateo-access-request-uid`, which the joiner flow sets on each user
it creates. It is visible and editable through the Admin API only: the user never sees it in the
account console, and the account API refuses a value the user sends for it (HTTP 400,
`error-user-attribute-read-only`). Add your own attributes after it; a
redeclared built-in fails the render. Changes made to the profile in the admin console are reverted
by the KOG. Uninstalling, or setting `userProfile.enabled: false`, leaves the realm's profile as it is.

## Events

The realm records user events (sign-ins and failures, the set-password link's credential change,
profile and email changes) and admin events (what administrators and service accounts change
through the Admin API), both kept for `realm.events.expiration` (90 days). Admin events store no
request body (`includeRepresentation: false`).

What Keycloak 26.6.3 records for the joiner flow, measured:

| step | recorded |
|---|---|
| the joiner flow creates the user | admin event `CREATE USER` |
| it sends the set-password email | admin event `ACTION USER users/<id>/execute-actions-email` (a failed send records nothing) |
| the user opens the link and sets a password | user event `UPDATE_CREDENTIAL` (no `EXECUTE_ACTION_TOKEN`, no `VERIFY_EMAIL`, though the email becomes verified) |
| the user signs in / mistypes the password | `LOGIN` / `LOGIN_ERROR` (`invalid_user_credentials`) |

`realm.events.types` must be Keycloak EventType names. Keycloak accepts any string there without
complaint, records nothing for an unknown one, and answers HTTP 500 to an event query by it. Up to
0.3.0 this chart enabled two names that do not exist (`SEND_EXECUTE_ACTIONS`, `SEND_ERROR`), so it
recorded no user events at all. CI now checks every enabled type against the pinned list.

Each type and listener may appear once. Keycloak keeps both lists as sets and keycloak-config-kog
compares them as sets, so a duplicate would never match the realm, which would be re-PUT and never
converge. Since 0.3.2 the chart refuses a duplicate at render, naming it, e.g.
`realm.events.types: "LOGIN" is listed twice`.

## Confidential clients (relying parties)

`clients[]` declares confidential OIDC clients for other services, such as Keystone federating with
the realm. Each one becomes a KeycloakClient (authorization code flow, the same bare-name `groups`
claim as the portal client, optional back-channel logout) whose secret External Secrets Operator
generates once into the Secret `<clientId>-client-secret` (key `client-secret`) in the release
namespace. The relying party syncs that one Secret into its own namespace, for example with an ESO
`ExternalSecret` on the Kubernetes provider, so Keycloak and the relying party always hold the same
value. The generated Secret is never regenerated (`refreshInterval: "0"`) and survives an uninstall
(`helm.sh/resource-policy: keep`): a new value would not reach Keycloak while the client's spec is
unchanged. Requires External Secrets Operator (already a keycloak-config-kog prerequisite).
[examples/openstack-keystone](../examples/openstack-keystone/values.yaml) is the realm Keystone uses,
with back-channel logout to Horizon.

## Mail

Password mode (`realm.smtp.authType: basic`): the Secret holds `username` and `password`.

Token mode (`realm.smtp.authType: token`, e.g. Microsoft 365, which disables password SMTP AUTH):
the Secret holds `username` (the sending mailbox) and `clientSecret` (the OAuth2 client secret);
`realm.smtp.token.url`, `.clientId` and `.scope` are values. Keycloak fetches a client-credentials
token and logs in with `AUTH XOAUTH2`. Place the Secret without echoing the secret or exposing it in
process arguments:

```console
$ read -rs -p 'client secret: ' CS && printf %s "$CS" | kubectl -n krateo-system create secret generic \
    keycloak-smtp --from-literal=username=noreply@example.com --from-file=clientSecret=/dev/stdin; unset CS
```

## Rotating credentials

Create a new Secret, set `realm.smtp.credentialsSecret.name` to it, upgrade, send a test email, then
delete the old Secret. The controller re-sends within about a minute (measured). Editing the
referenced Secret in place is never picked up (krateo-platformops/oasgen-provider#598). Microsoft
Entra client secrets expire (at most 24 months), so plan the rotation.

## Verifying

A wrong or missing credential does not fail at apply time: the realm reconciles, and sending fails
with HTTP 500 from execute-actions-email and `KC-SERVICES0029` in the Keycloak log. Keycloak stores
no `SEND_ERROR` event for an administrator-triggered email, so the caller's non-204 is the signal.

## Sign-in (authn)

Where authn is installed, the chart also renders authn's `OIDCConfig` (`oidcConfig.*`), derived from
the same client and groups, so the portal shows "Sign in with Keycloak". The client is public: authn
requires the portal's PKCE verifier and no secret exists.

authn does not verify ID-token signatures; it relies on receiving the token directly from the token
endpoint over **TLS** (OIDC Core 3.1.3.7). Keep that exchange on https:

- **Default:** authn reads discovery from the public `keycloakUrl`, over the public TLS certificate.
  The cluster's pods must reach that public host.
- **In-cluster:** set `discoveryUrl` to Keycloak's in-cluster **https** Service (a certificate authn
  trusts, e.g. from krateo-private-ca), and run Keycloak with `hostname-backchannel-dynamic: true` so
  the discovery document names in-cluster token and userinfo endpoints while the issuer and the
  browser's authorization endpoint stay public. Never point it at plain http: a forged token could
  carry any group.

Measured on GKE (authn 0.41.0, Keycloak 26.6.3, installed through a CompositionDefinition on
core-provider 2.13.82, in-cluster https discovery with a public issuer): the OIDCConfig is rendered;
a member of `tenants` signs in with PKCE and gets username `alice` and groups `[tenants]`; a user in
no allowed group is refused with 403.
