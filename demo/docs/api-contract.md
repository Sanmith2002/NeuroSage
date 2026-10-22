# Demo HTTP contract v1

Loopback local API; JSON UTF-8 only. Base `/api/demo`. Four operations. Exact fields and enums are defined in [data-model.md](data-model.md); implementation generates OpenAPI, then frontend DTOs. All presentation strings come from reviewed catalogs or fixed code maps. Responses use `Cache-Control: no-store`; no CORS wildcard or credentials. No authentication token, verifier secret or private fixture is returned.

| Method / path | Request | Response |
|---|---|---|
| GET `/health` | No parameters/body | 200 Health when ready; 503 Health otherwise |
| GET `/pipeline` | No parameters/body | 200 PipelineCatalog with four-screen content, eight features, six dimensions, historical evidence and limitations |
| GET `/scenarios` | No parameters/body | 200 ScenarioCatalog including qualified and explicitly unavailable categories; no raw fixture data |
| POST `/run` | RunRequest only | 200 AssessmentRun; 403 RejectedRun for real RuntimeAdmissionRejected; errors as below |

GET query parameters are rejected with fixed 422 if supplied; routes have no file/path/dataset selectors. The browser uses relative `/api/demo/...` via Vite proxy. Optional `/limitations` is omitted to avoid duplicated content. Backend docs/OpenAPI are development-only loopback routes; no input interface there may accept a raw Safira request.

Example request shape (ID remains pending qualification):

```json
{"scenario_id":"s-a71c"}
```

No static example response is represented as a performed run. At runtime, `kind:"assessment"` returns the **actual** service status and one of `cutoff_satisfied`, `cutoff_not_satisfied`, `required_evidence_unavailable`, `evidence_invalid`, `evidence_incompatible`, `evidence_not_ready`. Never return an individual score/probability, raw signal, association HMAC, artifact digest, correctness target or source ledger. Do not serialize the internal result wholesale.

403 `kind:"rejected"` is a demo transport projection of a framework exception, not a fourth Safira assessment status. It contains `disposition:"REJECTED"` and never `status`. Its reason enum is the pinned `_ADMISSION_REASONS` set: `input_invalid`, `trusted_evidence_missing`, `trusted_evidence_rejected`, `prediction_rejected`, `synthetic_fixture_rejected`, `registry_incompatible`, `scope_incompatible`, `original_reference_incompatible`, `original_inventory_incomplete`, `original_inventory_unverified`, `signal_reference_incompatible`, `signal_protocol_unapproved`, `artifact_invalid`, `artifact_incompatible`, `origin_rejected`, `policy_protocol_unapproved`. Use reviewed text per code; do not echo exception strings. Missing policies and construction errors are not admission exceptions; qualify or reject those recipes before publication.

## Safe HTTP failure matrix

| HTTP | ErrorEnvelope code | Meaning / UI behavior |
|---|---|---|
| 422 | `invalid_request` | Invalid JSON/schema, extra field, null/wrong type, unknown ID or query parameter; no run started |
| 413 | `request_too_large` | Body exceeds 2 KiB; fixed text, no body reflection |
| 415 | `unsupported_media_type` | Only application/json (optional UTF-8 charset) accepted |
| 403 | `origin_rejected` (ErrorEnvelope) | Foreign Origin fails transport check before framework; distinguish from RejectedRun via `kind` |
| 409 | `scenario_unavailable` | Known ID pending/unavailable; no fixture execution |
| 409 | `simulation_busy` | Single execution slot occupied; explicit retry control, no silent rerun |
| 503 | `demo_not_ready` | Worker/fixture startup not ready; no assessment |
| 504 | `simulation_timeout` | Worker terminated at deadline; mark result unknown/error, never DEFER |
| 500 | `internal_error` | Unexpected constructor/programming/provider fault; no upstream message, stack or fabricated trace |

Unmatched route/method remains 404/405 with a fixed safe error envelope where handlers apply. Default FastAPI/Pydantic validation details must be overridden: those can echo rejected input values. Error logging uses request ID, fixed route alias and fixed code only. No bodies or exception `repr`/cause chains.

Frontend client checks HTTP code **and** discriminant. Expected 403 RejectedRun renders the scientific admission rejection panel. Transport-origin 403 renders an ordinary error. 200 with an invalid shape is a protocol error, not success. No frontend classification math or fallback sample response. Abort/unmount discards stale responses; a browser abort does not mean worker execution was cancelled. No automatic replay of POST.

## Contract acceptance tests

Assert exact recursive response field sets and lifecycle literals; route inventory has no generic assessment/upload endpoint; malformed/unknown/extra fields cannot reach fixture lookup; no patient/correctness/private canaries in response/logs; service exception produces RejectedRun, programming exception ErrorEnvelope; unknown reasons fail closed as internal errors; `/pipeline` has precisely eight feature IDs and six exact dimensions; unavailable scenario cannot invoke service. Verify CORS/origin/Host rules and body-size middleware before Pydantic parsing.
