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
| `realm.registrationAllowed` | `false` | accounts only through the access-request flow |
| `realm.resetPasswordAllowed` / `verifyEmail` / `loginWithEmailAllowed` | `true` | |
| `realm.actionTokenGeneratedByAdminLifespan` | `259200` | set-password link lifetime, seconds (72 h) |
| `realm.events.{enabled,types,listeners}` | on, `SEND_EXECUTE_ACTIONS`/`SEND_ERROR`, `jboss-logging` | |
| `realm.smtp.enabled` | `false` | when true, `host` and `from` are required |
| `realm.smtp.{host,port,from,fromDisplayName,replyTo,auth,starttls,ssl}` | port `"587"`, auth/starttls `"true"`, ssl `"false"` | all strings |
| `realm.smtp.authType` | `basic` | `basic` or `token` |
| `realm.smtp.token.{url,clientId,scope}` | scope `https://outlook.office365.com/.default` | required in token mode |
| `realm.smtp.credentialsSecret.{name,userKey,passwordKey,clientSecretKey}` | `keycloak-smtp`, `username`, `password`, `clientSecret` | |
| `groups[]` | `tenants`, `platform-admins` | `{name, attributes?}`; names must not start with `/` or `system:` |
| `parentClient.{enabled,clientId,name,rootUrl}` | `true`, `krateo-portal`, `Krateo portal`, `""` | |
| `parentClient.redirectUris[]` | `[]` | **required** when enabled |
| `parentClient.webOrigins[]` / `postLogoutRedirectUris` / `groupsClaim` | `[]` / `"+"` / `groups` | |

Microsoft documents `https://outlook.office365.com/.default` as the SMTP client-credentials scope;
the Keycloak server admin guide's example shows `https://outlook.office.com/.default`. The token URL
embeds the Entra tenant id: identifying, not secret, and visible wherever values are readable.
