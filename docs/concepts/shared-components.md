# Shared components and providers

A `SharedComponent` is a pooled resource shared across environments. A typical example is a single Postgres instance where each environment gets its own database and credentials, but the underlying workload runs once. Each environment gets a consumer-specific slice provisioned on creation and torn down on deletion; the shared workload itself runs for the lifetime of the `SharedComponent`.

## SharedComponentProvider

A `SharedComponentProvider` defines the provisioning logic for a type of shared resource. It specifies:

- A Helm chart for the shared workload, deployed once per `SharedComponent`.
- An `instanceSecret` with static or generated keys. Generated keys are written once and never rotated, so the shared workload's admin credentials stay stable across environment churn.
- A `provision` Job script that runs once per environment to carve out a consumer slice (create a database, create a keyspace prefix, etc.).
- A `deprovision` Job script that runs when an environment is deleted.
- A `binding` template that renders into a Secret placed in the environment's workload namespace.

## Referencing shared component values

Components that depend on a shared component access its binding values with `{{.Components.NAME.KEY}}` in their Helm values or `env` blocks. This binds a component's configuration to whatever the shared component's provisioning wrote, such as a database URL or a credentials prefix.

## Consumer registration

Before the operator can provision a consumer slice, it must register the environment as a consumer under a Kubernetes Lease mutex in the management namespace (30-second duration). Only one environment reconcile can hold the Lease at a time; others requeue and retry on the next cycle.

While holding the Lease, the operator re-fetches the `SharedComponent` from the API server to confirm it is ready and has not reached `maxConsumers`. It then labels the environment's namespace as a consumer and re-fetches the `SharedComponent` one more time to verify it was not deleted between those two steps.

## Provisioning

After releasing the Lease, the operator writes a credentials Secret to the shared namespace, renders the provision script template, and submits the provision Job. When the Job succeeds, the credentials Secret is deleted and the binding Secret is written to the workload namespace so downstream components can consume it.

## Deprovisioning

On environment deletion, the operator re-creates the credentials Secret from the value stored in the binding Secret, then submits the deprovision Job. When that Job completes, the operator removes the Job, both Secrets, and the consumer namespace label. Storing the credentials in the binding Secret means the deprovision Job has access to the same credentials the provision Job used, regardless of how many other environments were created and destroyed in the meantime.
