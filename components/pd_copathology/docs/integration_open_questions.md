# Integration open questions (for the team)

The JSON input and output schemas (`input_schema_v1.json`, `output_schema_v1.json`) and the `python -m copath.inference` command
line are the integration boundary for now. No API, user interface, database model, persistence or authentication has been built;
these wait for the team's shared architecture decision. Questions that decision has to answer:

1. **Common patient / assessment identifier.** Which identifier does every component use? `participant_id` is currently echoed as
   supplied (may be pseudonymous). Is a separate assessment / visit identifier needed?
2. **Where do the raw features live?** Which component owns the baseline feature record, and in what form does it reach this component
   (file, message, request body)? Who maps their field names to `input_features_v1.md`?
3. **Who invokes the model?** A service, a batch job or an in-process library call? Is `predict_batch` enough, or is a long-running
   service needed (the bundle is verified once when loaded)?
4. **Storage of results.** How are a prediction run and its three signal results stored (for example `PredictionRun` / `SignalResult`)?
   Is the full JSON stored, or only parts of it?
5. **Is SHAP persisted?** If yes, only `top_features`, or the full contribution vector? Who may read it?
6. **What does the Clinical Predictive Safety Framework consume?** Probabilities only, or also `data_quality`, `top_features` and
   `cohort_in_training_scope`? Does it need the raw feature values (not included in the current output, for data minimisation)?
7. **What does the frontend show?** Probabilities, explanations, completeness? How is the research-proxy disclaimer displayed?
8. **Authentication and access control.** Who may submit records and read results?
9. **Result versioning.** How are `schema_version`, `model_version` and `selected_models_sha256` recorded so that a stored result can
   always be traced to the frozen bundle that produced it?
10. **Re-analysis and history.** What happens when a participant's record is updated or the model version changes: are old results kept,
    superseded or recomputed?
11. **Library-version policy.** Inference requires the exact scikit-learn version recorded in the packaging manifest. How is the
    deployment environment pinned and updated, and who approves a new compatibility test?
12. **Cohort and scope.** Who supplies `cohort`, and what should the consumer do with `cohort_in_training_scope = false`
    (that decision belongs to the Safety Framework)?
13. **Validation of value ranges and categorical codes.** Who is responsible for validating feature value ranges and categorical codes
    before model inference: the common backend/caller, the Clinical Predictive Safety Framework, or a future input-contract version such as v1.1?
