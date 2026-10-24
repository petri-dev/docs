# Deployment lifecycle and readiness

The operator moves each `EphemeralEnvironment` through five phases, committing every transition to status before proceeding.

## Phase transitions

### Pending

The entry point for every new environment. The operator allocates a workload namespace, creates it with ownership labels, creates the deployer `ServiceAccount` and a namespace-scoped `RoleBinding`, then commits the `NamespaceBound=True` condition as a durable lock on the namespace assignment. See [Namespaces, ownership, and isolation](namespaces.md) for how namespace names are derived and how ownership is verified.

After the namespace is bound, the operator registers shared component consumers under a Lease mutex, runs provision Jobs for each shared component, and writes binding Secrets into the workload namespace before advancing to Deploying.

### Deploying

The operator builds a dependency graph from the template's `dependsOn` entries using a topological sort (Kahn's algorithm), groups components into levels, and deploys level by level. Within each level, up to four components deploy in parallel. A component is done when its deployer Job succeeds and its readiness probe, if configured, returns 200. Once every component is ready, the operator advances to Ready.

### Ready

The operator checks the TTL on every reconcile. When `expiresAt` is in the past, it triggers deletion.

### Terminating

Set when the resource is deleted or when the TTL expires. The operator uninstalls Helm releases in reverse dependency order, runs deprovision Jobs for shared components, deletes the Ingress, then deletes the workload namespace using UID preconditions to prevent accidentally acting on a replacement namespace. Once cleanup is complete, the operator removes the finalizer.

### Failed

Set when a deployer Job exhausts its retries (5 attempts with exponential backoff) or when a readiness timeout is exceeded. Failed environments do not requeue automatically; they require manual intervention.

## Spec changes

Any change to `spec` is detected via `status.observedGeneration`. The operator resets component phases and re-runs the full deploy graph. Helm's install-or-upgrade semantics handle the case where a release already exists, so there is no delete-and-recreate on an image tag update or values change.

## Deployer Jobs

For each component deploy or undeploy, the operator creates a Kubernetes Job in the workload namespace. The Job runs the `petri-deployer` binary, which receives the operation as `PETRI_OP=deploy|undeploy` and a JSON spec as `PETRI_SPEC=...` through environment variables.

The deployer uses the Helm Go SDK directly. For a deploy, it initializes Helm action config with in-cluster credentials scoped to the target namespace, locates the chart (local path, Git fetch, or OCI registry), checks release history, and runs Install or Upgrade accordingly.

On failure, the deployer writes the error to `/dev/termination-log`, which the operator reads when observing the Job. The operator also cross-checks the Job's `PETRI_SPEC` against the current deploy options to detect stale Jobs left over from a previous reconcile cycle.
