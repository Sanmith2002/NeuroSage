# Output schema

Status: conceptual - field names and types are not frozen. The inference
contract is frozen only after final-model selection.

## Conceptual output

```
participant_id
model_version

signals:
  pd_type:
    probability
    top_features

  ad_like:
    probability
    top_features

  vascular_risk:
    probability
    top_features

data_quality:
  feature_completeness
  available_modalities
  missing_modalities
```

## Notes

- The three probabilities are research proxy signals, not clinical diagnoses.
- `top_features` carries the SHAP-based attributions for that signal.
- `data_quality` describes the input that was scored. It is descriptive only
  and is not a reliability judgement.

## What this component does not output

This component does not produce reliability scores, out-of-distribution flags,
or TRUST / CAUTION / DEFER decisions. The downstream Clinical Predictive Safety
Framework consumes this output and adds those decisions.
