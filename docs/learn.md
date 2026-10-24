# The concept of Petri

Petri manages short-lived application environments on Kubernetes. Define the
components once, create environments with their own inputs, and let the operator
handle deployment and cleanup.

## Architecture

Petri has three runtime components:

- **Operator:** reconciles environment resources, tracks readiness, and manages cleanup.
- **Deployer:** runs Helm operations in short-lived Jobs created by the operator.
- **API server:** provides an authenticated HTTP interface for managing environments.

The API server is optional when you use kubectl or GitOps directly.

[View the architecture](architecture.md) for the interactive component diagram
and deployment lifecycle.

## Core concepts

### Environment template

An `EnvironmentTemplate` defines reusable components: Helm charts, default values,
and dependencies. Several environments can share one template.

### Ephemeral environment

An `EphemeralEnvironment` references a template in the same namespace and supplies
environment-specific inputs, such as Helm values and a TTL. The operator deploys
its components and reports their status.

### Management and workload namespaces

Templates and environment resources live in a management namespace, such as
`default` in the quickstart. Each environment's applications and deployer Jobs run
in a separate namespace assigned by the operator. Its name is recorded in
`status.targetNamespace`.

### Time to live

A TTL such as `1h` tells the operator when to clean up an environment. It is
measured from creation time, not from when the application becomes ready. You
can also delete an environment manually before its TTL expires.

## FAQ

<details class="petri-faq" markdown="1">
<summary>Do I need the API server to use Petri?</summary>

No. You can apply Petri's custom resources directly with kubectl or GitOps.
The [quickstart](quickstart.md) uses this approach.

</details>

<details class="petri-faq" markdown="1">
<summary>Can I create an environment without a template?</summary>

Not currently. `EphemeralEnvironment.spec.template` must reference an existing
`EnvironmentTemplate` in the same namespace. Inline component definitions are
not supported in an `EphemeralEnvironment`.

</details>

<details class="petri-faq" markdown="1">
<summary>Do I install the deployer separately?</summary>

No. The operator's Helm chart configures its matching deployer image. The operator
creates deployer Jobs when it needs to install, upgrade, or uninstall releases.

</details>

<details class="petri-faq" markdown="1">
<summary>Does creating the resource mean my application is ready?</summary>

No. Deployment is asynchronous. Wait for the environment's `status.phase` to
become `Ready`. Inspect its component status and deployer logs if deployment fails.

</details>

<details class="petri-faq" markdown="1">
<summary>What happens when I delete an environment?</summary>

The operator runs cleanup and removes its workload namespace. The reusable
template remains. Keep the operator running until cleanup finishes.

</details>

<details class="petri-faq" markdown="1">
<summary>Does a separate namespace provide tenant isolation?</summary>

No, not by itself. Petri currently uses a single-tenant model. Each environment
has its own workload namespace, but this does not automatically provide network
isolation or per-tenant authorization. See [Namespaces, ownership, and isolation](concepts/namespaces.md)
for how workload namespaces are scoped and what they do and do not provide.

</details>

## Try it locally

[Follow the quickstart](quickstart.md) to install the operator in Kind and create
an ephemeral NGINX environment.
