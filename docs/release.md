---
type: Runbook
title: krateo-keycloak-realm — release
description: How a release ships: a plain-semver tag on a main commit that passed lint publishes the chart to GHCR and the Marketplace index (blueprints channel).
resource: oci://ghcr.io/krateo-blueprints/charts/krateo-keycloak-realm
tags: [release, oci, ghcr]
timestamp: 2026-11-11T00:00:00Z
---

# Release

Tag a commit on `main` whose `lint` run passed with a plain semver (`X.Y.Z`, no `v`). The
release-tag workflow stamps the version, pushes `oci://ghcr.io/krateo-blueprints/charts/krateo-keycloak-realm:X.Y.Z`
and publishes the same archive to the Marketplace index (channel `blueprints`). Verify that the OCI
archive's sha256 equals the index entry's digest.
