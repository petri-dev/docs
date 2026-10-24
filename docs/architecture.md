---
title: Architecture
wide: true
---

# Architecture

Petri is a Kubernetes operator for isolated, short-lived environments. You declare the services that make up an environment once, in an `EnvironmentTemplate`. Creating an `EphemeralEnvironment` resource - with kubectl, the API server, a CI job, or any other tool - causes the operator to deploy those services into a dedicated namespace, wait for readiness, and expose a URL. Deleting the resource, or letting its TTL expire, tears everything down.

<figure class="petri-architecture-figure">
<img src="../assets/architecture_light.svg" alt="Petri system architecture" class="petri-arch-light">
<img src="../assets/architecture_dark.svg" alt="Petri system architecture" class="petri-arch-dark">
</figure>

## Components

petri-operator is the only required component. It runs two controllers: one for environment lifecycle, one for shared component lifecycle. It watches `EphemeralEnvironment` CRs and drives them through phases, submits Helm deployer Jobs, manages shared infrastructure, and cleans up on deletion.

petri-apiserver is an optional HTTP gateway. It accepts REST calls, translates them into `EphemeralEnvironment` CRs, and reads status back out. You can skip it entirely and manage CRs directly with kubectl or any GitOps tool.

Deployer Jobs are short-lived Kubernetes Jobs the operator creates per component deploy or undeploy. They run the `petri-deployer` binary, which invokes Helm using the Go SDK. Jobs run as a `petri-deployer` ServiceAccount scoped to `admin` only within the workload namespace, so the operator itself requires no cluster-wide write access to workloads. Helm state is stored in Kubernetes Secrets (the default Helm backend).

## Resources

An `EnvironmentTemplate` describes the services that make up an environment: which charts to deploy, in what order, and how they connect. Component entries specify chart sources, Go template values rendered at deploy time, environment variable injections, dependency ordering, readiness probes, and optional references to shared infrastructure.

An `EphemeralEnvironment` CR represents one running environment. It references a template, optionally carries provenance metadata in `spec.source`, and accepts per-instance overrides for values and environment variables. The operator writes the current phase, workload namespace, URL, and per-component status back to `status`.

A `SharedComponent` is a pooled resource shared across environments, such as a single Postgres instance with one database per environment. A `SharedComponentProvider` defines the provisioning logic: the shared workload chart, credential generation, per-consumer provision and deprovision Job scripts, and the binding template that delivers connection details to each environment's workload namespace.

See [Templates and environments](concepts/templates-and-environments.md) and [Shared components and providers](concepts/shared-components.md) for full schema details.

## Environment lifecycle

The operator moves each environment through five phases: Pending (namespace allocation and shared component provisioning), Deploying (topological component deployment with parallel Jobs), Ready (TTL monitoring), Terminating (reverse undeploy and cleanup), and Failed (Job retry exhaustion or readiness timeout).

See [Deployment lifecycle and readiness](concepts/lifecycle.md) and [Namespaces, ownership, and isolation](concepts/namespaces.md) for the full mechanics.

## API server

The optional API server exposes an HTTP API for creating, reading, listing, and deleting environments without direct Kubernetes access. It validates OIDC tokens, checks organization and repository allowlists, and maps REST calls to `EphemeralEnvironment` CRs. See the [API server reference](apiserver/index.md) for endpoint details, authentication configuration, and upsert semantics.

## Observability

Both binaries emit Prometheus metrics on port 9090, Kubernetes Events on phase transitions, and JSON structured logs to stdout. See [Monitor Petri](operations/monitoring.md) for the full metric list and log format.

## Design decisions

The major non-obvious choices, including why Helm runs in Jobs rather than in-process, why the operator never reads Git repositories, and how the NamespaceBound condition prevents operating on the wrong namespace, are documented in [Implementation internals](contributing/internals.md).

## Source code

[Operator and deployer](https://github.com/petri-dev/petri-operator) /
[API server](https://github.com/petri-dev/petri-apiserver) /
[Documentation](https://github.com/petri-dev/docs)

[Start with the quickstart](quickstart.md).
