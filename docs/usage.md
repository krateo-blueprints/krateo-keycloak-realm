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

keycloak-config-kog >= 0.6.0 in the same namespace, its admin token Secret synced, and a Keycloak
>= 26.2 for token mail.

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
