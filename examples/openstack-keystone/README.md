---
type: Example
title: krateo-keycloak-realm — openstack-keystone example
description: The openstack realm Keystone federates with, as the OpenStack blueprint's S2 verification runs it - no portal client, one confidential keystone client with a generated secret and back-channel logout to Horizon.
resource: oci://ghcr.io/krateo-blueprints/charts/krateo-keycloak-realm
tags: [example, keystone, openstack, federation]
timestamp: 2026-11-13T00:00:00Z
---

# openstack-keystone

[values.yaml](values.yaml) declares the realm `openstack` with the group `tenants`, no portal client,
and one confidential client `keystone`:

- its redirect URI is Keystone's `OIDCRedirectURI` (the two strings must be byte-identical);
- its back-channel logout goes to Horizon's `/auth/backchannel-logout/` (logout tokens carry
  `aud: keystone`);
- its secret is generated once into `keystone-client-secret` (key `client-secret`) in the release
  namespace. Keystone's side syncs that Secret into `openstack` as its client secret, for example with
  an External Secrets `ExternalSecret` on the Kubernetes provider allowed to read only that Secret.

```console
$ helm install realm oci://ghcr.io/krateo-blueprints/charts/krateo-keycloak-realm \
    --version X.Y.Z -n keycloak-system -f examples/openstack-keystone/values.yaml
```

Keystone's federation (identity provider, mapping, protocol, per-tenant projects) comes from
krateo-openstack-federation.
