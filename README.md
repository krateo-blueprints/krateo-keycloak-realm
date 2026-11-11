# krateo-keycloak-realm

## What is this

A Helm chart that declares a Krateo platform's **parent Keycloak realm** as
[keycloak-config-kog](https://github.com/krateo-blueprints/krateo-keycloak-operator-kog) custom
resources: realm settings (self-registration off, set-password and verify-email links by email,
user events), its groups, and the portal's public PKCE OIDC client with a `groups` claim. The KOG's
controllers reconcile them against Keycloak and heal changes made in the Keycloak console.

## Install

Requires keycloak-config-kog >= 0.6.0 installed and authenticated against the target Keycloak.
Install in the KOG's namespace:

```console
$ helm install realm oci://ghcr.io/krateo-blueprints/charts/krateo-keycloak-realm \
    --version 0.1.0 -n krateo-system -f values.yaml
```

## Configure

See [docs/configuration.md](docs/configuration.md). The portal client's `redirectUris` is required;
outgoing mail is off until `realm.smtp.enabled`.

## Examples

- [examples/microsoft-365](examples/microsoft-365/README.md): the realm with Microsoft 365 mail
  (token / XOAUTH2 authentication).

## Docs

The bundle starts at [docs/index.md](docs/index.md).

## Develop & release

`hack/` holds the CI gates (schema `required` keys, Configuration `keep`, deletion policy). A
plain-semver tag releases the chart: [docs/release.md](docs/release.md).
