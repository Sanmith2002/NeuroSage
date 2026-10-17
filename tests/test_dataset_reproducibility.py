from safira.dataset import DatasetManifest, ExclusionRecord


def test_manifest_digest_is_canonical_and_changes_with_lineage():
    left=DatasetManifest("d","p","v1","1",{"b":"train","a":"validation"},("live","precomputed"),metadata={"seed":"s"})
    reordered=DatasetManifest("d","p","v1","1",{"a":"validation","b":"train"},("precomputed","live"),metadata={"seed":"s"})
    changed=DatasetManifest("d","p","v1","1",{"a":"train","b":"validation"},metadata={"seed":"s"})
    assert left.digest==reordered.digest
    assert left.digest!=changed.digest


def test_manifest_serialization_and_old_versions_are_detached():
    source={"nested":{"version":"v1"}}
    first=DatasetManifest("d","p","v1","1",{"g":"train"},metadata=source)
    second=DatasetManifest("d","p","v1","1",{"g":"train"},metadata={"nested":{"version":"v2"}})
    source["nested"]["version"]="changed"
    exported=first.to_dict(); exported["metadata"]["nested"]["version"]="changed-again"
    assert first.metadata["nested"]["version"]=="v1"
    assert first.digest!=second.digest


def test_controlled_exclusions_are_in_manifest_digest():
    a=DatasetManifest("d","p","v1","1",{},exclusions=(ExclusionRecord("opaque-ref","missing_outcome","join"),))
    b=DatasetManifest("d","p","v1","1",{},exclusions=(ExclusionRecord("opaque-ref","conflict","join"),))
    assert a.digest!=b.digest
