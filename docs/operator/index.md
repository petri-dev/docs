# Operator

[petri-operator](https://github.com/petri-dev/petri-operator) watches Petri resources
and reconciles them into Kubernetes workloads.

- `EnvironmentTemplate` defines reusable environment components.
- `EphemeralEnvironment` selects a template and supplies environment-specific inputs.

The operator handles deployment, updates, status, and cleanup. An API request succeeding
does not mean the resulting workload is ready. Check the environment's status.

## EnvironmentTemplate

An `EnvironmentTemplate` defines reusable components: Helm repositories, chart
versions, default values, and component dependencies. It can also set a default
TTL. Multiple environments can use the same template.

## EphemeralEnvironment

An `EphemeralEnvironment` selects a template through `spec.template` and supplies
environment-specific values and an optional TTL. The template must exist in the
same namespace. The current API requires a template. Helm components cannot be
defined inline in an `EphemeralEnvironment`.

Create resources directly with kubectl or GitOps, or use the
[API server](../apiserver/index.md) to manage environments over HTTP. Templates
are installed separately through Kubernetes.

## Deployer

The deployer runs Helm operations in short-lived Kubernetes Jobs created by the
operator. It installs or upgrades component releases during deployment and
uninstalls them during cleanup. Jobs run in the target workload namespace.

The operator chart configures the matching deployer image. There is no separate
deployer service to install. The operator observes Job completion and checks
workload readiness before marking the environment `Ready`.

The `ghcr.io/petri-dev/petri-operator:latest` and
`ghcr.io/petri-dev/petri-deployer:latest` image aliases track the latest stable
operator release. Prereleases do not update them. The Helm chart selects its
matching image versions automatically, so you do not need to override its image
tags to follow the quickstart.

## Workload namespaces

Each environment gets a dedicated `petri-env-*` namespace for its workloads and
deployer Jobs. The `EphemeralEnvironment` and its template remain in their
management namespace, such as `default` in the quickstart.

Read the actual workload namespace from `status.targetNamespace`. Do not derive
it from the environment name. The operator cleans up the environment when it is
deleted or its TTL expires. A dedicated namespace does not by itself provide
network isolation or per-user authorization.

See the [NGINX example](../quickstart.md#create-an-nginx-environment) for a complete
create, inspect, and delete walkthrough.

## Installation and examples

The operator is distributed as an OCI Helm chart:

```bash
helm upgrade --install petri oci://ghcr.io/petri-dev/charts/petri \
  --namespace petri-system --create-namespace --wait
```

Follow the [quickstart](../quickstart.md) to run the operator in a local Kind cluster.
See [resource examples](https://github.com/petri-dev/petri-operator/tree/main/config/samples)
and [operator releases](https://github.com/petri-dev/petri-operator/releases).
