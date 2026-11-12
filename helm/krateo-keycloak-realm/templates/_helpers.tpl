{{- define "kr.labels" -}}
app.kubernetes.io/name: krateo-keycloak-realm
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "kr.deletionPolicy" -}}
krateo.io/deletion-policy: {{ .Values.deletionPolicy }}
{{- end -}}

{{- define "kr.configurationRef" -}}
configurationRef:
  name: {{ .Values.configuration.name }}
  namespace: {{ .Release.Namespace }}
{{- end -}}

{{- /* A Kubernetes object name derived from a Keycloak name (e.g. a group "platform-admins"). */ -}}
{{- define "kr.objName" -}}
{{- . | lower | replace "_" "-" | replace " " "-" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "kr.check" -}}
{{- /* Keycloak stores the realm's event types and listeners as sets, and the KOG compares them as
sets: a duplicate here never matches what Keycloak returns, so the realm would be re-PUT and never
converge. Refuse it at render, naming the key and the value. A render check rather than uniqueItems
in values.schema.json, which crdgen would turn into a CRD-level constraint on existing resources. */ -}}
{{- range $key := list "types" "listeners" -}}
{{- $seen := dict -}}
{{- range (index $.Values.realm.events $key | default list) -}}
{{- if hasKey $seen (toString .) -}}
{{- fail (printf "realm.events.%s: %q is listed twice (Keycloak keeps these as a set; remove the duplicate)" $key (toString .)) -}}
{{- end -}}
{{- $_ := set $seen (toString .) true -}}
{{- end -}}
{{- end -}}
{{- range .Values.groups -}}
{{- if or (hasPrefix "/" .name) (hasPrefix "system:" .name) (hasPrefix "krateo:" .name) -}}
{{- fail (printf "group %q: a group name must not start with \"/\" (a group path), \"system:\" (reserved for Kubernetes) or \"krateo:\" (reserved for authn, e.g. krateo:loa:2)" .name) -}}
{{- end -}}
{{- end -}}
{{- if .Values.userProfile.enabled -}}
{{- $seen := dict "username" true "email" true "firstName" true "lastName" true -}}
{{- range .Values.userProfile.attributes -}}
{{- if not .name -}}
{{- fail "userProfile.attributes: every attribute needs a name" -}}
{{- end -}}
{{- if hasKey $seen .name -}}
{{- fail (printf "userProfile.attributes: %q is declared twice, or redeclares a built-in (username, email, firstName and lastName come from Keycloak's default profile)" .name) -}}
{{- end -}}
{{- $_ := set $seen .name true -}}
{{- end -}}
{{- end -}}
{{- if and .Values.parentClient.enabled (not .Values.parentClient.redirectUris) -}}
{{- fail "parentClient.redirectUris is required when parentClient.enabled (e.g. https://cmp.example.com/auth?kind=oidc)" -}}
{{- end -}}
{{- if .Values.realm.smtp.enabled -}}
{{- if or (not .Values.realm.smtp.host) (not .Values.realm.smtp.from) -}}
{{- fail "realm.smtp.host and realm.smtp.from are required when realm.smtp.enabled" -}}
{{- end -}}
{{- if and (eq .Values.realm.smtp.authType "token") (or (not .Values.realm.smtp.token.url) (not .Values.realm.smtp.token.clientId) (not .Values.realm.smtp.token.scope)) -}}
{{- fail "realm.smtp.token.url, .clientId and .scope are required when realm.smtp.authType is token" -}}
{{- end -}}
{{- if and (eq .Values.realm.smtp.authType "token") (ne (.Values.realm.smtp.auth | toString) "true") -}}
{{- fail "realm.smtp.authType token needs realm.smtp.auth \"true\"" -}}
{{- end -}}
{{- end -}}
{{- end -}}
