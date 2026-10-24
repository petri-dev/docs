# Namespaces, ownership, and isolation

Petri uses three distinct namespace roles. The management namespace holds all custom resources (`EphemeralEnvironment`, `EnvironmentTemplate`, `SharedComponent`, `SharedComponentProvider`) and is where the operator runs. The shared namespace holds shared workloads deployed by `SharedComponent` resources. Each environment gets its own workload namespace where Helm releases and per-environment resources live.

## Namespace naming

Each workload namespace is derived from the environment's Kubernetes UID:

```
petri-env-<hex(SHA256(uid))[:n]>
```

The operator starts with 8 hex characters. If that name is taken by a namespace it does not own, it tries progressively longer prefixes: 12, 16, 20, and so on up to 52 characters. This gives 62 characters total including the `petri-env-` prefix, staying within the [63-character limit for DNS labels](https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#dns-label-names).

The operator never constructs the namespace name from the environment name. To find the namespace for an environment, read it from `status.targetNamespace`:

```sh
kubectl get ephemeralenvironment <name> -n <management-namespace> \
  -o jsonpath='{.status.targetNamespace}'
```

## Ownership

A namespace is owned by an environment only when it carries both labels:

- `petri.run/managed=true`
- `petri.run/environment-uid=<full UID>`

A namespace with only `petri.run/managed=true` is never adopted, even if its name matches the derived prefix. Both labels must be present.

## NamespaceBound condition

`status.targetNamespace` is written to the API server before the namespace is created. The `NamespaceBound=True` condition, set immediately after, acts as a durable lock: once committed, the namespace assignment is never reconsidered, not on controller restarts, not on spec changes, and not if a shorter hash prefix becomes available later.

This means that reading `status.targetNamespace` is always reliable: the value there is the one the operator will use for all subsequent operations, including cleanup.

## Deletion safety

On deletion, the operator reads the namespace directly from the API server rather than from the informer cache, which could be stale. It then verifies ownership using UID and resourceVersion preconditions before taking any action, so a replacement namespace created with the same name is never accidentally deleted.
