{{- /*
The effective values: this chart's defaults (files/values.defaults.yaml, a copy of values.yaml that CI
keeps equal) with the supplied values merged over them. `helm upgrade --reuse-values` upgrades with the
PREVIOUS release's values and does not apply the new chart's defaults, so a key added since (e.g.
userProfile in 0.3.0, realm.adminEvents in 0.3.1) would be missing and fail with a nil pointer. Every
template and helper reads values through this. Explicit empty values (false, "", []) still win.
*/ -}}
{{- define "kr.values" -}}
{{- $defaults := .Files.Get "files/values.defaults.yaml" | fromYaml | default dict -}}
{{- toYaml (mergeOverwrite (deepCopy $defaults) (deepCopy .Values)) -}}
{{- end -}}

{{- define "kr.labels" -}}
app.kubernetes.io/name: krateo-keycloak-realm
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "kr.deletionPolicy" -}}
{{- $v := include "kr.values" . | fromYaml -}}
krateo.io/deletion-policy: {{ $v.deletionPolicy }}
{{- end -}}

{{- define "kr.configurationRef" -}}
{{- $v := include "kr.values" . | fromYaml -}}
configurationRef:
  name: {{ $v.configuration.name }}
  namespace: {{ .Release.Namespace }}
{{- end -}}

{{- /* A Kubernetes object name derived from a Keycloak name (e.g. a group "platform-admins"). */ -}}
{{- define "kr.objName" -}}
{{- . | lower | replace "_" "-" | replace " " "-" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "kr.check" -}}
{{- $v := include "kr.values" . | fromYaml -}}
{{- /* Keycloak stores the realm's event types and listeners as sets, and the KOG compares them as
sets: a duplicate here never matches what Keycloak returns, so the realm would be re-PUT and never
converge. Refuse it at render, naming the key and the value. A render check rather than uniqueItems
in values.schema.json, which crdgen would turn into a CRD-level constraint on existing resources. */ -}}
{{- range $key := list "types" "listeners" -}}
{{- $seen := dict -}}
{{- range (index $v.realm.events $key | default list) -}}
{{- if hasKey $seen (toString .) -}}
{{- fail (printf "realm.events.%s: %q is listed twice (Keycloak keeps these as a set; remove the duplicate)" $key (toString .)) -}}
{{- end -}}
{{- $_ := set $seen (toString .) true -}}
{{- end -}}
{{- end -}}
{{- $ids := dict -}}
{{- if $v.parentClient.enabled -}}{{- $_ := set $ids $v.parentClient.clientId true -}}{{- end -}}
{{- range $v.clients -}}
{{- if not .clientId -}}
{{- fail "clients: every client needs a clientId" -}}
{{- end -}}
{{- if hasKey $ids .clientId -}}
{{- fail (printf "clients: clientId %q is declared twice (or equals parentClient.clientId)" .clientId) -}}
{{- end -}}
{{- $_ := set $ids .clientId true -}}
{{- if not .redirectUris -}}
{{- fail (printf "clients[%s].redirectUris is required: the relying party's exact redirect URI (e.g. Keystone's OIDCRedirectURI)" .clientId) -}}
{{- end -}}
{{- end -}}
{{- range $name, $c := dict "identityLifecycle" $v.identityLifecycle "ideClient" $v.ideClient -}}
{{- if $c.enabled -}}
{{- if not $c.clientId -}}
{{- fail (printf "%s.clientId is required when %s.enabled" $name $name) -}}
{{- end -}}
{{- if hasKey $ids $c.clientId -}}
{{- fail (printf "%s.clientId %q is already used by another client of this chart" $name $c.clientId) -}}
{{- end -}}
{{- $_ := set $ids $c.clientId true -}}
{{- end -}}
{{- end -}}
{{- if $v.identityLifecycle.enabled -}}
{{- if or (not $v.identityLifecycle.secret.name) (not $v.identityLifecycle.secret.key) -}}
{{- fail "identityLifecycle.secret.name and .key are required when identityLifecycle.enabled (the Secret identity-lifecycle mounts)" -}}
{{- end -}}
{{- if or (not $v.identityLifecycle.roleClientId) (not $v.identityLifecycle.roles) -}}
{{- fail "identityLifecycle.roleClientId and .roles are required when identityLifecycle.enabled" -}}
{{- end -}}
{{- $seen := dict -}}
{{- range $v.identityLifecycle.roles -}}
{{- if hasKey $seen (toString .) -}}
{{- fail (printf "identityLifecycle.roles: %q is listed twice (compared as a set; remove the duplicate)" (toString .)) -}}
{{- end -}}
{{- $_ := set $seen (toString .) true -}}
{{- end -}}
{{- end -}}
{{- if $v.ideClient.enabled -}}
{{- if not $v.ideClient.audience -}}
{{- fail "ideClient.audience is required when ideClient.enabled: the MCP resource the gateway expects in the access token's aud (e.g. https://cmp.example.com/mcp)" -}}
{{- end -}}
{{- if not $v.ideClient.redirectUris -}}
{{- fail "ideClient.redirectUris is required when ideClient.enabled (e.g. http://localhost:* and http://127.0.0.1:*)" -}}
{{- end -}}
{{- end -}}
{{- range $v.groups -}}
{{- if or (hasPrefix "/" .name) (hasPrefix "system:" .name) (hasPrefix "krateo:" .name) -}}
{{- fail (printf "group %q: a group name must not start with \"/\" (a group path), \"system:\" (reserved for Kubernetes) or \"krateo:\" (reserved for authn, e.g. krateo:loa:2)" .name) -}}
{{- end -}}
{{- end -}}
{{- if $v.userProfile.enabled -}}
{{- $seen := dict "username" true "email" true "firstName" true "lastName" true -}}
{{- range $v.userProfile.attributes -}}
{{- if not .name -}}
{{- fail "userProfile.attributes: every attribute needs a name" -}}
{{- end -}}
{{- if hasKey $seen .name -}}
{{- fail (printf "userProfile.attributes: %q is declared twice, or redeclares a built-in (username, email, firstName and lastName come from Keycloak's default profile)" .name) -}}
{{- end -}}
{{- $_ := set $seen .name true -}}
{{- end -}}
{{- end -}}
{{- if and $v.parentClient.enabled (not $v.parentClient.redirectUris) -}}
{{- fail "parentClient.redirectUris is required when parentClient.enabled (e.g. https://cmp.example.com/auth?kind=oidc)" -}}
{{- end -}}
{{- if $v.realm.smtp.enabled -}}
{{- if or (not $v.realm.smtp.host) (not $v.realm.smtp.from) -}}
{{- fail "realm.smtp.host and realm.smtp.from are required when realm.smtp.enabled" -}}
{{- end -}}
{{- if and (eq $v.realm.smtp.authType "token") (or (not $v.realm.smtp.token.url) (not $v.realm.smtp.token.clientId) (not $v.realm.smtp.token.scope)) -}}
{{- fail "realm.smtp.token.url, .clientId and .scope are required when realm.smtp.authType is token" -}}
{{- end -}}
{{- if and (eq $v.realm.smtp.authType "token") (ne ($v.realm.smtp.auth | toString) "true") -}}
{{- fail "realm.smtp.authType token needs realm.smtp.auth \"true\"" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- /* A confidential client's secret, generated ONCE by External Secrets Operator into a Secret.
Args: obj (object-name prefix), name/key (target Secret), length, root (the top context). */ -}}
{{- define "kr.generatedClientSecret" -}}
---
# The client secret, generated once by External Secrets Operator into {{ .name }}. The KOG reads it
# into the client (clientSecretRef); the client's owner reads the same Secret (a relying party such as
# Keystone syncs it into its own namespace; identity-lifecycle mounts it). refreshInterval "0" never
# regenerates it, and `keep` lets it survive an uninstall: a new value is not re-pushed to Keycloak
# while the client's spec is unchanged, so a regenerated secret would silently diverge from the one
# the client's owner holds.
apiVersion: generators.external-secrets.io/v1alpha1
kind: Password
metadata:
  name: {{ .obj }}-secret
  namespace: {{ .root.Release.Namespace }}
  labels:
    {{- include "kr.labels" .root | nindent 4 }}
  annotations:
    helm.sh/resource-policy: keep
spec:
  length: {{ .length | default 48 }}
  digits: 10
  symbols: 0
  noUpper: false
  allowRepeat: true
---
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: {{ .obj }}-secret
  namespace: {{ .root.Release.Namespace }}
  labels:
    {{- include "kr.labels" .root | nindent 4 }}
  annotations:
    helm.sh/resource-policy: keep
spec:
  refreshInterval: "0"
  target:
    name: {{ .name }}
    creationPolicy: Owner
    template:
      data:
        {{ .key }}: {{ "{{ .password }}" | quote }}
  dataFrom:
    - sourceRef:
        generatorRef:
          apiVersion: generators.external-secrets.io/v1alpha1
          kind: Password
          name: {{ .obj }}-secret
{{- end -}}
