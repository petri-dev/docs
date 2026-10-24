# Monitor Petri

Both binaries expose Prometheus metrics on port 9090. The metrics endpoint has no authentication; keep it internal to your cluster.

## Operator metrics

| Metric | Type | Description |
| --- | --- | --- |
| `petri_environment_phase_transitions_total` | counter | Phase transitions. Label: `phase` |
| `petri_environment_deploy_duration_seconds` | histogram | Time from entering Deploying to entering Ready |
| `petri_environment_deploy_failures_total` | counter | Environments that entered the Failed phase |

Metrics are recorded after the status PATCH succeeds to avoid double-counting on reconcile retries.

## API server metrics

| Metric | Type | Labels |
| --- | --- | --- |
| `petri_http_requests_total` | counter | `route`, `method`, `status` |
| `petri_http_request_duration_seconds` | histogram | `route`, `method`, `status` |

## Kubernetes Events

The operator emits one Kubernetes Event per phase transition on the `EphemeralEnvironment` resource. Transitions to Deploying, Ready, and Terminating emit `Normal` events. Transitions to Failed emit `Warning` events.

## Logs

Both binaries write JSON structured logs to stdout.

The API server logs one access record per request, containing the route, method, request ID, status code, and duration. It also logs one audit record per mutating call, containing the action, resource name, namespace, result, and the verified OIDC issuer and subject.

Neither binary logs tokens, request bodies, or OIDC claim values.
