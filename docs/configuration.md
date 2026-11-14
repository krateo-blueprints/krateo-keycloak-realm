---
type: Configuration
title: krateo-keycloak-realm — configuration
description: The values surface: deletion policy, the KOG Configuration and token Secret, realm settings and mail (password or token), groups, and the portal client.
resource: oci://ghcr.io/krateo-blueprints/charts/krateo-keycloak-realm
tags: [configuration]
timestamp: 2026-11-11T00:00:00Z
---

# Configuration

| value | default | meaning |
|---|---|---|
| `deletionPolicy` | `orphan` | `orphan`: deleting a resource leaves the Keycloak object; `delete`: removes it |
| `resourceGroup` | `keycloak.ogen.krateo.io` | the KOG's API group (match keycloak-config-kog's `resourceGroup`) |
| `configuration.name` | `keycloak-admin` | name of the per-kind Configurations |
| `configuration.tokenSecret.{name,key}` | `keycloak-admin-token` / `token` | the KOG's token Secret, in the release namespace |
| `realm.name` / `displayName` / `enabled` | `krateo` / `Krateo` / `true` | |
| `realm.registrationAllowed` | `false` | accounts only through an administrator-approved joiner flow |
| `realm.resetPasswordAllowed` / `verifyEmail` / `loginWithEmailAllowed` | `true` | |
| `realm.actionTokenGeneratedByAdminLifespan` | `259200` | set-password link lifetime, seconds (72 h) |
| `realm.events.{enabled,types,listeners}` | on, 23 types (logins, the set-password link, credential/profile/email changes), `jboss-logging` | `types` must be Keycloak EventType names: CI checks them against `hack/testdata/keycloak-26.6.3-event-types.json` |
| `realm.events.expiration` | `7776000` (90 days) | seconds Keycloak keeps user events, and admin events when they are on |
| `realm.adminEvents.{enabled,includeRepresentation}` | `true` / `false` | record Admin API changes; `includeRepresentation` would store each change's JSON body (personal data for users) |
| `realm.smtp.enabled` | `false` | when true, `host` and `from` are required |
| `realm.smtp.{host,port,from,fromDisplayName,replyTo,auth,starttls,ssl}` | port `"587"`, auth/starttls `"true"`, ssl `"false"` | all strings |
| `realm.smtp.authType` | `basic` | `basic` or `token` |
| `realm.smtp.token.{url,clientId,scope}` | scope `https://outlook.office365.com/.default` | required in token mode |
| `realm.smtp.credentialsSecret.{name,userKey,passwordKey,clientSecretKey}` | `keycloak-smtp`, `username`, `password`, `clientSecret` | |
| `groups[]` | `tenants`, `platform-admins` | `{name, attributes?}`; names must not start with `/`, `system:` or `krateo:` |
| `userProfile.enabled` | `true` | render the realm's whole user profile (needs keycloak-config-kog >= 0.7.0): Keycloak's default `username`, `email`, `firstName`, `lastName` verbatim, then `attributes` |
| `userProfile.attributes[]` | `krateo-access-request-uid` (admin view/edit only, length <= 36) | Keycloak attribute shape: `name`, `displayName`, `group`, `multivalued`, `validations`, `annotations`, `required`, `permissions{view,edit}`, `selector`; a built-in name is refused |
| `parentClient.{enabled,clientId,name,rootUrl}` | `true`, `krateo-portal`, `Krateo portal`, `""` | |
| `parentClient.redirectUris[]` | `[]` | **required** when enabled: the **portal frontend's** OIDC callback page, not an authn URL (authn never receives the browser redirect; the frontend passes it the code). Rendered into both the client's `redirectUris` and the OIDCConfig's `redirectURI`. With path-based exposure it must not fall under another component's prefix: if authn is routed at `/auth`, a callback under `/auth` reaches authn and sign-in fails. |
| `parentClient.webOrigins[]` / `postLogoutRedirectUris` / `groupsClaim` | `[]` / `"+"` / `groups` | |
| `clients[]` | `[]` | confidential relying parties (e.g. Keystone): `{clientId, name?, redirectUris (required), webOrigins?, postLogoutRedirectUris?, groupsClaim?, backchannelLogout{url, sessionRequired}?, secret{name, key, length}?}` |
| `clients[].secret` | name `<clientId>-client-secret`, key `client-secret`, length 48 | the Secret External Secrets Operator generates once for the client |
| `identityLifecycle.enabled` | `false` | identity-lifecycle's own client: confidential, service account only, plus a KeycloakServiceAccountRoleMapping (needs keycloak-config-kog >= 0.8.0) |
| `identityLifecycle.{clientId,secret.name,secret.key}` | `identity-lifecycle`, `identity-lifecycle-idp`, `clientSecret` | the client and the generated Secret identity-lifecycle mounts (`accessRequest.keycloak.clientSecretRef`) |
| `identityLifecycle.{roleClientId,roles[]}` | `realm-management`, `manage-users`/`view-users`/`query-groups` | exactly the roles its service account holds; a duplicate is refused |
| `ideClient.enabled` / `clientId` / `name` | `false` / `krateo-ide` / `Krateo IDE (MCP)` | the public client IDEs sign in with for the MCP endpoint |
| `ideClient.audience` | `""` (unset) | **required** when enabled (the render refuses an empty value): the MCP resource the gateway expects in the access token's `aud`, byte-for-byte (`https://<portal host>/mcp`, no trailing slash) |
| `ideClient.redirectUris[]` / `groupsClaim` | `http://localhost:*`, `http://127.0.0.1:*` / `groups` | loopback only (the IDE picks the port) |
| `oidcConfig.enabled` / `name` | `true` / `keycloak` | render authn's OIDCConfig (only where the `oidc.authn.krateo.io/v1alpha1` API exists); `name` is the `?name=` of `/oidc/login` |
| `oidcConfig.keycloakUrl` | `""` | **required** when enabled: Keycloak's public base URL (the keycloak chart's `keycloak.hostname`); issuer = `<keycloakUrl>/realms/<realm.name>` |
| `oidcConfig.discoveryUrl` | `""` | where authn reads discovery; empty = `<issuer>/.well-known/openid-configuration` |
| `oidcConfig.allowedGroups[]` | `[]` | empty = every name in `groups` |
| `oidcConfig.additionalScopes` | `""` | |
| `oidcConfig.graphics.{displayName,icon,backgroundColor,textColor}` | `Sign in with Keycloak`, `key`, `""`, `""` | the login button |

Microsoft documents `https://outlook.office365.com/.default` as the SMTP client-credentials scope;
the Keycloak server admin guide's example shows `https://outlook.office.com/.default`. The token URL
embeds the Entra tenant id: identifying, not secret, and visible wherever values are readable.
