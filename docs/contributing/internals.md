# Implementation internals

This page describes the reasoning behind several non-obvious design choices in the operator and API server.

## Jobs instead of in-process Helm

The operator creates a Kubernetes Job for each component deploy or undeploy rather than calling Helm inside the reconcile loop. This means the operator needs no write RBAC in workload namespaces: the deployer ServiceAccount, scoped to `admin` within the workload namespace only, is what Helm uses. Each deploy leaves a pod with logs, giving a clear audit trail. Jobs also survive controller restarts mid-deploy without leaving orphaned state, and they isolate Helm SDK state between concurrent deploys running in parallel.

## The operator never reads application repositories

Artifact references (image tags, chart versions) are resolved by whoever creates the `EphemeralEnvironment` and passed in as `spec.values`. The operator is stateless with respect to source control and holds no Git credentials. `spec.source` carries provenance metadata (repo, branch, sha) for external tooling to consume; the operator ignores it entirely.

## NamespaceBound is a durable lock

`status.targetNamespace` is committed to the API server before the namespace is created, and the `NamespaceBound=True` condition locks the assignment. Once set, the assignment is never reconsidered on controller restarts, on spec changes, or if a shorter hash prefix becomes available later. The cleanup path always reads the namespace from `status.targetNamespace` and verifies ownership before acting. This prevents a class of bugs where a restarted controller derives a different namespace name and operates on the wrong one.

## Generated secrets are stable

The `instanceSecret` for a shared workload writes its keys once and never rotates them. The generated value is stored in the binding Secret placed in the environment's workload namespace. This means the deprovision Job always has access to the same credentials the provision Job used, regardless of how many environments were created and destroyed in between.

## Spec changes re-deploy in place

When `spec` changes, the operator detects it via `status.observedGeneration`, resets component phases, and re-runs the full deploy graph. Helm's upgrade semantics handle the case where a release already exists, so an image tag update or a values change does not require deleting and recreating the environment.

## Single-tenant today

One management namespace holds all custom resources for one Petri installation. The shared namespace is a placement namespace for shared workloads and is not a tenant or access-control boundary. Tenant identity, project scoping, and multi-cluster placement are planned for a future phase.
