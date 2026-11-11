{{- define "kr.labels" -}}
app.kubernetes.io/name: krateo-keycloak-realm
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
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
{{- range .Values.groups -}}
{{- if or (hasPrefix "/" .name) (hasPrefix "system:" .name) -}}
{{- fail (printf "group %q: a group name must not start with \"/\" (a group path) or \"system:\" (reserved for Kubernetes)" .name) -}}
{{- end -}}
{{- end -}}
{{- if and .Values.parentClient.enabled (not .Values.parentClient.redirectUris) -}}
{{- fail "parentClient.redirectUris is required when parentClient.enabled (e.g. https://cmp.example.com/auth?kind=oidc)" -}}
{{- end -}}
{{- if .Values.realm.smtp.enabled -}}
{{- if or (not .Values.realm.smtp.host) (not .Values.realm.smtp.from) -}}
{{- fail "realm.smtp.host and realm.smtp.from are required when realm.smtp.enabled" -}}
{{- end -}}
{{- end -}}
{{- end -}}
