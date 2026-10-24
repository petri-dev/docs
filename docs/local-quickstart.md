# Run the API server locally

This is the second part of the quickstart. Add a local API server to the cluster
from [Your first environment](quickstart.md), then use it to create another NGINX
environment over HTTP.

The operator keeps running in Kind. The API server runs in a Docker container on
Kind's network and uses a separate kubeconfig to access that cluster.

## Before you begin

Complete the first quickstart through [Open NGINX](quickstart.md#open-nginx).
Stop the port-forward with Ctrl-C and skip cleanup. You need the `petri-dev`
cluster, the installed operator, and `nginx-template` in the `default` namespace.
If you already deleted the cluster, repeat the first quickstart before continuing.

Use the Docker and Kind installation from the first quickstart, plus curl 7.82.0
or newer. Keep ports 8080 and 9090 available on your machine. No source checkout
or Go toolchain is needed.

You will use two terminals:

- **Terminal 1:** the terminal from the first quickstart, with its temporary
  `KUBECONFIG` still set. Run the API server here.
- **Terminal 2:** a new terminal for HTTP requests. It does not need a kubeconfig.

## Check the existing cluster

In Terminal 1:

```bash
kubectl config current-context
kubectl get environmenttemplate nginx-template --namespace default
```

The context should be `kind-petri-dev`, and the template should exist. If either
check fails, return to the first quickstart and confirm the cluster and kubeconfig
before starting the server.

## Prepare the container

In Terminal 1, pull the latest stable API-server image:

```bash
docker pull ghcr.io/petri-dev/petri-apiserver:latest
```

Create a separate kubeconfig for use inside Docker:

```bash
PETRI_CONTAINER_KUBECONFIG="$(mktemp)"
kind get kubeconfig --name petri-dev --internal > "$PETRI_CONTAINER_KUBECONFIG"
```

The `--internal` address is reachable from containers on Kind's `kind` Docker
network. The host kubeconfig from the first quickstart uses a localhost address
that would point back to the API-server container itself. Keep the original
`KUBECONFIG` unchanged for your host-side `kubectl` commands.

## Run the API server

In Terminal 1:

```bash
docker run --rm --name petri-apiserver \
  --network kind \
  --user "$(id -u):$(id -g)" \
  --mount "type=bind,source=$PETRI_CONTAINER_KUBECONFIG,target=/kubeconfig,readonly" \
  -p 127.0.0.1:8080:8080 \
  -p 127.0.0.1:9090:9090 \
  -e KUBECONFIG=/kubeconfig \
  -e PETRI_APISERVER_AUTH_MODE=token \
  -e PETRI_APISERVER_ALLOW_INSECURE_TOKEN=true \
  -e PETRI_APISERVER_TOKEN=dev-only-change-me \
  -e PETRI_APISERVER_NAMESPACE=default \
  -e PETRI_APISERVER_ADDR=:8080 \
  -e PETRI_APISERVER_METRICS_ADDR=:9090 \
  ghcr.io/petri-dev/petri-apiserver:latest
```

Leave the container running. The API is available at `127.0.0.1:8080` on your
machine, and metrics are available at `127.0.0.1:9090`. Inside the container, the
listeners bind to all interfaces so Docker can forward these ports.

The kubeconfig is mounted read-only. Running with your user ID lets the container
read the private temporary file without changing its permissions. These credentials
grant access to the disposable Kind cluster, so use this setup only for local
development. Deployed installations should use
[OIDC and the deployment's service account](apiserver/index.md#deployment-and-metrics).

## Check the API

In Terminal 2, set the endpoint and token:

```bash
export PETRI_API_URL='http://127.0.0.1:8080'
export PETRI_TOKEN='dev-only-change-me'
```

Check readiness:

```bash
curl -sS --fail-with-body -i "$PETRI_API_URL/readyz"
```

Expect HTTP `200`. Then make an authenticated request to list templates:

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $PETRI_TOKEN" \
  "$PETRI_API_URL/v1/templates"
```

The response should include the template from the first quickstart:

```json
{
  "items": [
    {
      "name": "nginx-template",
      "components": [{"name": "web"}]
    }
  ]
}
```

If the list is empty, check that the template is in `default` and that Terminal 1
uses the intended cluster. A `401` means the request token is missing or does not
match the local server's token.

## Create an environment over HTTP

In Terminal 2, create `api-demo` using the existing template:

```bash
curl -sS --fail-with-body -i \
  -H "Authorization: Bearer $PETRI_TOKEN" \
  --json '{
    "name": "api-demo",
    "template": "nginx-template",
    "ttl": "1h"
  }' \
  "$PETRI_API_URL/v1/environments"
```

Expect HTTP `201` for a new environment. A repeated request returns `200` because
POST creates or updates by name. The operator deploys the workload asynchronously.

Read its status:

```bash
curl -sS --fail-with-body \
  -H "Authorization: Bearer $PETRI_TOKEN" \
  "$PETRI_API_URL/v1/environments/api-demo"
```

Repeat the GET request every few seconds until `phase` becomes `Ready`. Allow
up to five minutes for this sample. If it reports `Failed` or does not become
ready, inspect the operator and deployer logs as in the first quickstart.
The one-hour TTL starts at environment creation.

You now have a local API server connected to the operator and an environment
created through HTTP. Keep the server and cluster running if you want to experiment further.

## Cleanup

When you have finished, delete the environment from Terminal 2:

```bash
curl -sS --fail-with-body -i -X DELETE \
  -H "Authorization: Bearer $PETRI_TOKEN" \
  "$PETRI_API_URL/v1/environments/api-demo"
```

Expect `204` for accepted deletion. If the TTL already expired, you may get `404`
because the environment is gone.

Stop the API-server container with Ctrl-C in Terminal 1. Docker removes the
container because it was started with `--rm`. The operator continues running
in Kind, so it can finish cleanup. In that terminal, wait for deletion:

```bash
kubectl wait --namespace default --for=delete \
  ephemeralenvironment/api-demo --timeout=5m
```

Finally, delete the disposable cluster, including the first quickstart's
environment and the reusable template:

```bash
kind delete cluster --name petri-dev
rm -f "$PETRI_CONTAINER_KUBECONFIG"
unset KUBECONFIG
```

If you used a custom `KUBECONFIG` before the quickstarts, restore it in Terminal 1.
