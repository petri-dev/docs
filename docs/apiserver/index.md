# API server

[petri-apiserver](https://github.com/petri-dev/petri-apiserver) provides an HTTP API
over Petri resources in one Kubernetes management namespace.

| Method | Path | Auth | Operation |
| --- | --- | --- | --- |
| GET, HEAD | `/healthz` | none | Always 200; liveness check |
| GET, HEAD | `/readyz` | none | 200 or 503; checks namespace and CRD access |
| POST | `/v1/environments` | bearer | Create or update an environment |
| GET, HEAD | `/v1/environments` | bearer | List environments (paginated) |
| GET, HEAD | `/v1/environments/{name}` | bearer | Read one environment |
| DELETE | `/v1/environments/{name}` | bearer | Request deletion |
| GET, HEAD | `/v1/templates` | bearer | List templates (name and component names) |

Workload deployment and deletion are asynchronous. The operator performs reconciliation.

## Authentication

OIDC is the default. Configure `PETRI_APISERVER_OIDC_ISSUER`,
`PETRI_APISERVER_OIDC_AUDIENCE`, and at least one organization or repository allowlist
with its corresponding claim mapping. Send `Authorization: Bearer <token>` on requests.

All admitted identities share access to environments in the management namespace.
There is no per-user or per-repository ownership isolation. Static-token mode is for
explicitly opted-in development, as shown in [Run the API server locally](../local-quickstart.md).

## Deployment and metrics

The server's [deployment example](https://github.com/petri-dev/petri-apiserver/tree/main/config)
includes a Deployment, Service, ServiceAccount, and required RBAC. Supply your image and
the `petri-apiserver-config` Secret with OIDC settings.

`/healthz` and `/readyz` are public. Prometheus metrics are served separately at
`/metrics` on port 9090 by default. Keep that unauthenticated listener internal.

- `petri_http_requests_total`: completed requests.
- `petri_http_request_duration_seconds`: request duration histogram.

Both use `route`, `method`, and `status` labels. Configure alerts in your monitoring system.

## GitHub Actions OIDC

To admit workflows from one repository, create this configuration Secret before
installing the API server. Replace `your-org/your-repo`:

```bash
kubectl create secret generic petri-apiserver-config --namespace default \
  --from-literal=PETRI_APISERVER_AUTH_MODE=oidc \
  --from-literal=PETRI_APISERVER_OIDC_ISSUER=https://token.actions.githubusercontent.com \
  --from-literal=PETRI_APISERVER_OIDC_AUDIENCE=petri-apiserver \
  --from-literal=PETRI_APISERVER_OIDC_REPOSITORY_CLAIM=repository \
  --from-literal=PETRI_APISERVER_ALLOWED_REPOSITORIES=your-org/your-repo
```

If the server is already installed, update its existing Secret and restart the
Deployment. Omit the organization allowlist when restricting access to individual
repositories: an organization match would admit other repositories from that organization.

Set a GitHub Actions repository variable named `PETRI_API_URL` to your externally
reachable HTTPS API endpoint, without a trailing slash. Add the following workflow
to the admitted repository. The runner must be able to reach that endpoint. A
local `kubectl port-forward` is not reachable from a GitHub-hosted runner.

```yaml
name: Check Petri access
on:
  workflow_dispatch:
permissions:
  id-token: write
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - name: Request an OIDC token and list templates
        env:
          PETRI_API_URL: ${{ vars.PETRI_API_URL }}
        shell: bash
        run: |
          set -euo pipefail
          token="$(curl --fail-with-body --silent --show-error \
            -H "Authorization: Bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" \
            "${ACTIONS_ID_TOKEN_REQUEST_URL}&audience=petri-apiserver" \
            | jq -er '.value')"
          printf '::add-mask::%s\n' "$token"
          curl --fail-with-body \
            -H "Authorization: Bearer $token" \
            "$PETRI_API_URL/v1/templates"
```

This uses the GitHub-issued OIDC JWT, not a PAT or `GITHUB_TOKEN`. Obtain a fresh
token for each job that calls Petri. The repository allowlist does not restrict
branches, workflow files, or ownership of environments within Petri's management
namespace.
