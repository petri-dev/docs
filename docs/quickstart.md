# Quickstart

Run the Petri operator in a local Kubernetes cluster, then create an ephemeral
NGINX environment using Kubernetes custom resources.

## Prerequisites

Install [Docker](https://docs.docker.com/get-started/get-docker/),
[Kind](https://kind.sigs.k8s.io/docs/user/quick-start/),
[kubectl](https://kubernetes.io/docs/tasks/tools/), and
[Helm](https://helm.sh/docs/intro/install/). Make sure Docker is running.

Run the commands below in the same terminal.

## Create a local cluster

Use a separate kubeconfig for the test cluster:

```bash
export KUBECONFIG="$(mktemp)"
kind create cluster --name petri-dev \
  --kubeconfig "$KUBECONFIG"

kubectl get nodes
```

Kind uses the default Kubernetes image for your installed Kind release.
The `petri-dev-control-plane` node should report `Ready`.

## Install the operator

```bash
helm install petri oci://ghcr.io/petri-dev/charts/petri \
  --namespace petri-system --create-namespace \
  --wait --timeout 5m
```

Helm selects the latest stable chart release. The chart installs the operator,
its custom resource definitions (CRDs), and the
required permissions. It also configures the matching deployer image, which the
operator uses to create Jobs when an environment is deployed.

## Verify the installation

```bash
kubectl rollout status deployment/petri-controller-manager \
  --namespace petri-system --timeout=120s

kubectl get pods --namespace petri-system

kubectl get crd environmenttemplates.core.petri.run \
  ephemeralenvironments.core.petri.run
```

The rollout should complete successfully, the operator pod should show `1/1`
ready and `Running`, and both CRDs should be present. The operator is now ready
to manage Petri environments.

If the operator does not start, inspect its logs and pod events:

```bash
kubectl logs --namespace petri-system deployment/petri-controller-manager --tail=100
kubectl describe pods --namespace petri-system
```

For image pull failures, check that Docker and the cluster can reach `ghcr.io`.

## Create an NGINX environment

Run the following command to create an ephemeral NGINX environment in `default`
with a one-hour TTL. The example uses Helm's public `hello-world` chart and requires
access to `helm.github.io` and Docker Hub.

```bash
kubectl apply -f - <<'EOF'
apiVersion: core.petri.run/v1alpha1
kind: EnvironmentTemplate
metadata:
  name: nginx-template
  namespace: default
spec:
  components:
    - name: web
      helm:
        repo: https://helm.github.io/examples
        chart: hello-world
        values:
          image.repository: nginx
          image.tag: stable-alpine
          service.type: ClusterIP
---
apiVersion: core.petri.run/v1alpha1
kind: EphemeralEnvironment
metadata:
  name: nginx-demo
  namespace: default
spec:
  template: nginx-template
  ttl: "1h"
EOF
```

Wait for the environment to become ready:

```bash
kubectl wait --namespace default ephemeralenvironment/nginx-demo \
  --for=jsonpath='{.status.phase}'=Ready --timeout=5m
```

The operator creates a dedicated workload namespace and a deployer Job, then
waits for NGINX to become ready. The environment expires one hour after creation.

Read the assigned namespace from the environment's status:

```bash
export PETRI_WORKLOAD_NAMESPACE="$(kubectl get ephemeralenvironment nginx-demo \
  --namespace default -o jsonpath='{.status.targetNamespace}')"

kubectl get jobs,pods,deployments,services --namespace "$PETRI_WORKLOAD_NAMESPACE"
```

Expect a completed `petri-deploy-nginx-demo-web` Job and a ready
`nginx-demo-web-hello-world` Deployment.

If the wait times out, inspect the environment and deployer logs:

```bash
kubectl describe ephemeralenvironment nginx-demo --namespace default
kubectl logs --namespace "$PETRI_WORKLOAD_NAMESPACE" \
  job/petri-deploy-nginx-demo-web --container deployer --tail=100
```

The Job logs are available once the operator has assigned a namespace and started
the deployer.

## Open NGINX

In the same terminal, start a port-forward:

```bash
kubectl port-forward --namespace "$PETRI_WORKLOAD_NAMESPACE" \
  service/nginx-demo-web-hello-world --address 127.0.0.1 8081:80
```

Leave it running and open <http://127.0.0.1:8081> in your browser. You should see
the **Welcome to nginx!** page.

## Continue with the API server

To manage environments over HTTP, continue with
[Run the API server locally](local-quickstart.md). Stop the port-forward with
Ctrl-C, but keep this cluster, the `nginx-template`, and the terminal with your
temporary kubeconfig. Skip the cleanup below until you finish the second part.

## Cleanup

Stop the port-forward with Ctrl-C. In the same terminal, delete the environment
and wait for its workload namespace to disappear:

```bash
kubectl delete ephemeralenvironment nginx-demo --namespace default --timeout=5m
kubectl wait --for=delete "namespace/$PETRI_WORKLOAD_NAMESPACE" --timeout=5m
kubectl delete environmenttemplate nginx-template --namespace default
```

Keep the operator running until cleanup finishes. The template is reusable and
is not deleted automatically with the environment. If the one-hour TTL has
already expired, the environment may already be gone.

Finally, delete the local cluster:

```bash
kind delete cluster --name petri-dev
unset KUBECONFIG
```

This removes the cluster and everything installed in it, including the operator
and CRDs. If you previously used a custom `KUBECONFIG`, restore that value in your
shell after cleanup.
