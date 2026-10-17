import pytest

from safira.dataset import DatasetCompatibilityError
from safira.dataset.validation import correctness, validate_binding
from tests.dataset_fixtures import target_and_binding


class Label:
    positive_outcome="positive"
    negative_outcome="negative"


class Prediction:
    source_key=("m","v1","label-a")
    class Primary: predicted_class="positive"; value=.2
    primary=Primary()


def test_target_uses_only_registered_class_and_verified_binary():
    target,binding=target_and_binding("m","v1","label-a")
    validate_binding(target,binding,Prediction(),Label())
    assert correctness(Prediction(),1,target,binding)==1
    assert correctness(Prediction(),0,target,binding)==0


def test_binding_is_exact_and_score_does_not_change_target():
    target,binding=target_and_binding("m","v1","label-a")
    bad=binding.__class__(binding.target_id,binding.target_version,"other","v1",binding.label_id,"positive","negative")
    with pytest.raises(DatasetCompatibilityError): validate_binding(target,bad,Prediction(),Label())
    assert correctness(Prediction(),1,target,binding)==1
