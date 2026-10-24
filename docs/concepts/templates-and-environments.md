# Templates and environments

An `EnvironmentTemplate` describes the services that make up a preview environment: which Helm charts to deploy, in what order, and how they connect. It is typically set up once per cluster; individual environments supply per-instance overrides on top of it.

## EnvironmentTemplate

Each component entry in a template specifies a Helm chart source, which can be a path in a Git repository, a separate Git repository with an optional fallback ref, or a published OCI or Helm registry chart.

Component entries also accept:

- `values` - Go template strings rendered at deploy time. Available variables include `{{.Env.Name}}`, `{{.Env.Slug}}`, `{{.Env.GeneratedSecret}}`, and `{{.Components.NAME.KEY}}` for binding values from shared components.
- `env` - environment variables injected via Helm. Entries can be plain strings or references to a shared component binding Secret.
- `dependsOn` - component names that must reach the Ready phase before this component starts deploying.
- `readiness` - an optional HTTP health check the operator polls before advancing dependent components.
- `sharedComponentRef` - a reference to a `SharedComponent` instead of a Helm chart, used when a component is pooled across environments.

At the template level, you can configure the ingress domain pattern (a Go template accepting `{{.Name}}`), a default TTL applied to all environments that do not set their own, and a deploy timeout per component (default 15 minutes).

## EphemeralEnvironment

One `EphemeralEnvironment` CR represents one running environment. You create it with kubectl, the API server, a CI job, or any other tool that can write Kubernetes resources. The operator picks it up and drives it through its lifecycle.

```yaml
apiVersion: petri.run/v1alpha1
kind: EphemeralEnvironment
metadata:
  name: my-environment
  namespace: <management namespace>
spec:
  template: default
  source:             # optional metadata; the operator never reads the repository
    repo: https://github.com/org/myapp
    branch: feature/my-feature
    sha: abc123def
  values:             # flat map; keys are Helm dot-notation paths
    image.tag: abc1234
  env:                # per-environment env overrides
    FEATURE_X: "true"
  ttl: 48h            # overrides template TTL; "0" disables expiry
```

`spec.source` is provenance metadata only. The operator never clones or reads the repository; whoever creates the `EphemeralEnvironment` is responsible for resolving artifact references and passing them in as `spec.values`.

`spec.values` and `spec.env` replace their entire map in the template when supplied. Passing `{}` clears the map. Omitting a field leaves the template's map in place.

## Status

The operator writes the current state back to `status`:

```yaml
status:
  phase: Ready          # Pending | Deploying | Ready | Failed | Terminating
  targetNamespace: petri-env-a3f2c1b9
  url: https://my-environment.preview.example.com
  expiresAt: "2026-07-25T10:00:00Z"
  components:
    - name: postgres
      phase: Ready
      shared: true
    - name: api
      phase: Ready
    - name: frontend
      phase: Ready
```

`targetNamespace` is the workload namespace allocated for this environment. `url` is the ingress URL rendered from the template's domain pattern. `expiresAt` reflects the effective TTL; it is absent when TTL is disabled. Each component entry in `status.components` tracks its own phase and whether it is backed by a shared component.

See [Deployment lifecycle and readiness](lifecycle.md) for how the operator moves an environment through its phases.
