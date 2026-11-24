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

## identity-lifecycle's client

`identityLifecycle.enabled: true` renders the client identity-lifecycle authenticates with for access
requests: confidential, service account only (no browser flow, no password grant), its secret generated
once into `identity-lifecycle-idp` (key `clientSecret`) for identity-lifecycle to mount. A
`KeycloakServiceAccountRoleMapping` keeps its service account holding **exactly** `realm-management`
`manage-users`, `view-users` and `query-groups`: a role added by hand is removed. Needs
keycloak-config-kog >= 0.8.0, whose delegated kinds need Snowplow and authn wired into the
rest-dynamic-controller deployment.

## The IDE client (MCP)

`ideClient.enabled: true` renders `krateo-ide`, the client IDEs such as Claude Code and Cursor sign in
with when they reach the platform's MCP endpoint (`claude mcp add --transport http <name>
https://<portal host>/mcp --client-id krateo-ide --callback-port <port>`). It is public (no secret),
authorization code with PKCE S256 only, and redirects to any loopback port. Its access token carries
`preferred_username`, the same bare-name `groups` claim as the portal client, and `mcp.audience`
(`ideClient.audience` before 0.7.0) in `aud`, which the MCP gateway compares byte-for-byte. Set it per install; it has no default. The
issuer is the realm's, the same as the portal's, so authn matches the IDE's user to their portal user.

**Known limit in 0.5.0, gone on current oasgen-provider.** The client has two protocol mappers
(`groups`, `mcp-audience`). Keycloak returns them in its own order, and rest-dynamic-controller up to
oasgen-provider 0.63.1 compared a list of objects by position, so after creating the client correctly
its KeycloakClient latched `Ready=False` with `DriftNotConverging`. Sign-in worked; the condition was
wrong. With oasgen-provider 0.74.0 both `krateo-krateo-ide` and `krateo-krateo-portal` reach
`Available` (measured 2026-11-16 through the installer, krateo-keycloak-realm 0.5.3, Keycloak 26).

## Personal agents: Hermes and anonymous registration (0.7.0)

Personal agents reach the same MCP endpoint as IDEs, and their access tokens must carry the same three claims authn's
`/delegate` reads: `preferred_username`, bare-name `groups`, and `mcp.audience` in `aud`. Lightweight access tokens stay
off on every MCP client: they would drop `sid`, which authn requires of a user token.

**Hermes** (`hermesClient.enabled`) is pre-registered: `hermes`, public, PKCE S256, redirect exactly
`http://127.0.0.1/callback`. Keycloak matches a registered `http://127.0.0.1/<path>` on **any port** (measured on 26.6.3)
and refuses `localhost`, so Hermes must bind `127.0.0.1`.

**The `mcp` client scope** is rendered whenever any MCP client is on, and assigned as **optional** to `krateo-ide` and
`hermes` (`KeycloakClientOptionalClientScope`). Every MCP client requests `scope=mcp`, which the gateway advertises, and
Keycloak answers a requested scope the client does not hold with a hard `invalid_scope` (measured). A client's scope list
is create-only in Keycloak, so the assignment is its own CR and also works on a client that already exists. These two
clients carry the same claims inline; a token then holds the audience and `groups` once (measured).

**Anonymous registration** (`agentRegistration.enabled`) lets an agent such as OpenClaw register its own client at
`/realms/<realm>/clients-registrations/openid-connect`, with no admin token. The chart makes that safe:

| Object | What it enforces |
|---|---|
| `mcp` client scope (fixed id) + 3 `KeycloakClientScopeProtocolMapper`s | the claims above. The agent registers with `"scope": "mcp offline_access"` and authorizes with the same; `"openid mcp"` at registration is refused. The scope's id is derived from the realm name, so the mappers can name it; they follow `mcp.audience` when the host changes (Keycloak ignores mappers on a scope update, hence one CR per mapper) |
| Trusted Hosts (adopted) | redirect and client URIs only on `127.0.0.1`; the registering host is not checked (agents register from anywhere) |
| Allowed Client Scopes (adopted) | `mcp` and `offline_access`, plus the realm's own default and default-optional scopes (`email`, `profile`, `roles`, `phone`, ...): `allow-default-scopes` stays `true`, because Keycloak refuses a registration otherwise. Any other scope of the realm, or an unknown one, is refused (measured). OpenClaw always asks for `offline_access`: its MCP SDK adds it whenever discovery offers it |
| Max Clients Limit (adopted) | `agentRegistration.maxClients` registered clients in the realm |
| `krateo client-disabled` (created) | every registered client starts **disabled** until a realm admin enables it |
| `agent-dcr` client profile + policy | on anonymous registrations: PKCE S256, loopback http only, full scope off, and a redirect of exactly `http://127.0.0.1[:port]/oauth/mcp/callback` (OpenClaw with its Gateway running) or `/oauth/callback` (its CLI login). `localhost`, public hosts and any other path are refused |
| `CLIENT_REGISTER`, `CLIENT_DELETE` event types | added to `realm.events.types`: identity-lifecycle's cleanup finds clients registered more than 7 days ago and never enabled from these events and the realm's admin events |

At sign-in a registered client may request exactly the scopes it registered for, plus `openid`; anything else is
`invalid_scope` (measured). Full scope is off on registered clients, so requesting `roles` adds no role the client is not mapped to, and every scope a
client asks for is listed on the consent screen.

A registered client requires **consent**, so the user's first sign-in shows Keycloak's consent screen ("Offline Access",
"mcp"). Its refresh token is an **offline** one; `realm.offlineSessions.maxLifespan` (default 30 days) caps it, so an agent
signs in again at least every 30 days. The cap is realm-wide and applies to every client's offline sessions; `0` removes it
(Keycloak's default, under which an offline session that keeps being used never expires). Removing a user from their group
takes effect at the agent's next refresh: the new access token has no `groups`, and authn refuses it.

**Ending an agent's access** is done in Keycloak, and takes effect at the agent's next refresh: it lasts until the current
access token expires, and authn issues nothing that outlives that token (at most 15 minutes per exchange). authn verifies
tokens, not Keycloak sessions, and has no sign-out of its own. Measured on 26.6.3, with one browser sign-in shared by the
portal, an IDE and an agent:

| Action | The agent's offline session |
|---|---|
| the user signs out of the portal | **keeps working** (the portal's and the IDE's sessions end) |
| an administrator signs the user out (Sessions, Sign out) | **keeps working** |
| revoking the user's consent to the client | ends, for good |
| disabling the client | stops; enabling it again **revives the same token** |
| disabling the user | stops while disabled |
| removing the user from their group | the refreshed token has no `groups`, so authn refuses it |

To end one agent for good, revoke the consent. An agent works only for a person who has signed in to the portal at least
once.

The three default policies are **adopted** (found by name and sub-type) and always `orphan`, whatever `deletionPolicy`
says: deleting a CR must never remove a constraint from the realm. The client profiles and policies CRs own the realm's
**whole** (non-global) profile and policy lists.

Registration requires the realm's user events to be on and kept at least 14 days, and its admin events to be on, or the
render fails: the cleanup reads registrations older than 7 days, and a client an admin enabled and later disabled (an
admin event on it) is never cleaned up.

## Changing the spec can delete keys from the realm's attributes

Keycloak fills some maps with server-side keys the chart does not declare, and the KOG's update sends
each map **whole**. What that does depends on the object, so it was measured rather than assumed
(2026-11-16, oasgen-provider 0.74.0: a free-form probe key seeded through the Admin API, then a spec
change through the installer, Keycloak read before and after):

| object | map | on a spec-change update |
|---|---|---|
| `KeycloakRealm krateo` | `attributes` | **keys are deleted**: the probe key and `realmReusableOtpCode` were gone. Seven defaults (`ciba*`, `oauth2DeviceCodeLifespan`, `oauth2DevicePollingInterval`, `parRequestUriLifespan`) came back, because Keycloak regenerates them, so a check that watched only those would pass for the wrong reason |
| `KeycloakClient krateo-krateo-portal`, `krateo-krateo-ide` | `attributes` | **nothing is deleted**: Keycloak's client update keeps keys the request omits (the probe and `backchannel.logout.*`, `realm_client` all survived a real update) |

oasgen-provider 0.74.0's `UnmodelledKeysWouldBeRemoved` Warning names keys for both kinds; for clients
it is a false positive, since the warning cannot tell a vendor that replaces a map from one that merges
it. It fires only on a resync and compares one level deep, so its silence is not evidence either.

So anything set on the realm's `attributes` outside the chart (by hand or by another tool) is lost on
the next spec change. The chart deliberately does not copy Keycloak's defaults into the CR: Keycloak
adds defaults between releases, and a copied list would silently miss the new ones. The fix is
keycloak-config-kog declaring these maps as partial fields (merged with what Keycloak holds), which
needs oasgen-provider >= 0.77.0. Until that release, keep spec changes rare.

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
