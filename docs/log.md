---
type: Log
title: krateo-keycloak-realm — log
description: Curated history of krateo-keycloak-realm.
resource: oci://ghcr.io/krateo-blueprints/charts/krateo-keycloak-realm
tags: [log, history]
timestamp: 2026-11-11T00:00:00Z
---

# Log

## 2026-11-14 — `parentClient.redirectUris` is the frontend's callback (docs)

Found while planning a path-mode install (krateo-057): the portal client's redirect URI is the portal
**frontend's** OIDC callback page, which hands the code to authn; authn never receives the browser
redirect. With host-based exposure `https://<portal host>/auth?kind=oidc` reaches the frontend (authn
has its own host). With path-based exposure authn is routed at `/auth` on the same host, so that URL
reaches authn instead and sign-in fails after a successful Keycloak login. Values comments, schema text
and configuration docs now say so. No rendered object changes.

## 2026-11-13 — 0.5.1: `ideClient.audience` described consistently

0.5.0 described `ideClient.audience` as "no default" while its schema (correctly) carries `default: ""`,
so a consumer reading both had to choose which to believe (reported by the installer). It is empty by
default, meaning unset, and the render refuses an empty value when `ideClient.enabled`; the schema,
values comments and configuration docs now say exactly that. No rendered object changes.

## 2026-11-13 — 0.5.0: identity-lifecycle's client and the IDE client

Proven in-cluster (disposable GKE, keycloak-config-kog 0.8.0, oasgen-provider 0.63.1 with the rdc
snowplow/authn wiring): the client and its exact role set converge, hand-made drift is reverted, and
deleting the role mapping removes the roles. `identityLifecycle.enabled` renders identity-lifecycle's own client for access requests (confidential,
service account only, secret generated once into `identity-lifecycle-idp`/`clientSecret` for it to
mount) and a `KeycloakServiceAccountRoleMapping` holding its service account to exactly
`realm-management` `manage-users`, `view-users`, `query-groups` (keycloak-config-kog >= 0.8.0).
`ideClient.enabled` renders `krateo-ide`, the public PKCE client IDEs sign in with for the MCP endpoint:
loopback redirects, lightweight access tokens off, bare-name `groups` and `ideClient.audience` (required,
no default) in the access token. Known limit: its two protocol mappers make its KeycloakClient latch
`DriftNotConverging` until rest-dynamic-controller compares lists of objects by key (requested from
oasgen-provider); the client itself is correct in Keycloak. Both are off by default, so existing installs render unchanged. The
client-secret objects moved into a shared helper (`kr.generatedClientSecret`); `clients[]` renders the
same objects. `hack/check-clients.py`, `check-deletion-policy.py` and `check-configurations-keep.py` now
render every optional client.

## 2026-11-13 — 0.4.0: confidential clients for relying parties

`clients[]` renders confidential KeycloakClients for other services (first user: Keystone federation in
the OpenStack blueprint's S2 verification). Each client's secret is generated once by External Secrets
Operator (a `Password` generator and an `ExternalSecret`, both kept on uninstall) into
`<clientId>-client-secret`, which the client reads through `clientSecretRef` and the relying party
syncs into its own namespace. Optional OIDC back-channel logout (`backchannel.logout.url`, session
required by default). The client Configuration is rendered when only `clients` are declared. CI gate
`hack/check-clients.py`. New key `clients` (default `[]`), so existing installs render unchanged.

## 2026-11-12 — 0.3.3: upgrades with `helm upgrade --reuse-values` work

`helm upgrade --reuse-values` to 0.3.0, 0.3.1 or 0.3.2 failed from an older release with a nil pointer
(`userProfile` from 0.1.0 or 0.2.0, `realm.adminEvents` from 0.3.0): reuse-values upgrades with the
previous release's values and does not apply the new chart's defaults. Every template and helper now
reads values through `kr.values`, which merges the chart's defaults (`files/values.defaults.yaml`, a
copy of values.yaml that CI keeps equal; Helm does not expose values.yaml through `.Files`) under the
supplied values. Explicit `false`, `""` and `[]` still win. Fresh renders are byte-identical to 0.3.2
(default values, the Microsoft 365 example, and an override set with `false` and an empty list). CI
gate `hack/check-reuse-values.py` renders under the values of 0.1.0 to 0.3.2 and requires the same
objects as a default render.

## 2026-11-12 — 0.3.2: duplicate event types and listeners are refused at render

`realm.events.types` and `realm.events.listeners` are sets in Keycloak, and keycloak-config-kog 0.7.1
with oasgen-provider 0.62.0 compares them as sets, so a duplicate in values could never converge (the
realm would be re-PUT and latch `Ready=False`). The chart now fails the render with the key and the
value, e.g. `realm.events.types: "LOGIN" is listed twice`. It is a render-time check on purpose, not
`uniqueItems` in values.schema.json: crdgen turns that into `x-kubernetes-list-type: set` on the
Composition (and Installer) CRDs, a validation tightening on resources that already exist. No CRD field
and no values key changed; the defaults (23 types, 1 listener) are duplicate-free. CI
(`hack/check-event-types.py`) requires a duplicate in either list to fail with that message.

Also measured for 0.3.1 on demo's upgrade path (GKE, oasgen 0.62.0): keycloak-config-kog 0.7.0 with
realm 0.3.1 re-PUT the realm every 3 minutes; `helm upgrade` of the KOG to 0.7.1 alone made it up to
date on the next observation and `Ready=True`, with no controller restart.

## 2026-11-12 — 0.3.1: user and admin events that actually record

Up to 0.3.0 the realm enabled two user event types that are not Keycloak EventTypes
(`SEND_EXECUTE_ACTIONS`, `SEND_ERROR`). Keycloak stored them, recorded nothing, and answered HTTP 500
to queries by them, so the realm kept no user events. 0.3.1 enables 23 real types, keeps events for 90
days (`realm.events.expiration`), and turns admin events on without request bodies
(`realm.adminEvents`; their retention is the realm attribute `adminEventsExpiration`). CI checks every
enabled type against `hack/testdata/keycloak-26.6.3-event-types.json`, the `/admin/serverinfo` list of
Keycloak 26.6.3 (132 types, identical to its `EventType.java`).

Also: `smtpServer.authType` (and the token fields) are rendered only when `realm.smtp.auth` is
`"true"`. Keycloak drops `authType` when auth is off, so the CR never matched the realm.

Measured on GKE (Keycloak 26.6.3) through the joiner flow; see [usage](usage.md#events).

Requires keycloak-config-kog >= 0.7.1 and oasgen-provider >= 0.62.0 (annotations
`krateo.io/requires-*`). Keycloak returns the event types in its own order: with 23 of them,
oasgen-provider 0.61.0 PUT the realm four times, 3 minutes apart, then stopped ("Drift is not
converging") and left it `Ready=False`; 0.62.0 with keycloak-config-kog 0.7.1 issued no PUT over 15
minutes and kept it `Ready=True`, while still restoring an event type removed out of band with one PUT.

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
