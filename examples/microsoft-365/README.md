---
type: Example
title: krateo-keycloak-realm — Microsoft 365 example
description: The parent realm with Microsoft 365 mail in token (XOAUTH2) mode and the portal client.
resource: oci://ghcr.io/krateo-blueprints/charts/krateo-keycloak-realm
tags: [example, microsoft-365]
timestamp: 2026-11-11T00:00:00Z
---

# Microsoft 365 mail

Values in [values.yaml](values.yaml). Before installing, place `krateo-system/keycloak-smtp` with keys
`username` (the sending mailbox) and `clientSecret` (see [usage](../../docs/usage.md)). On the
Microsoft side the Entra application needs the `SMTP.SendAsApp` application permission with admin
consent, an Exchange Online service principal with send rights on the mailbox, and SMTP AUTH enabled
for that mailbox.
