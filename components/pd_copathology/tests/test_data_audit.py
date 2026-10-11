"""Tests for the Phase 1 dataset audit (copath.data.audit).

Everything runs against the synthetic download built by
``tests/fixtures/build_fixtures.py``. No test reads PPMI data.
"""

from __future__ import annotations

import io
import json
import re

import pandas as pd
import pytest

from copath.data import archive, privacy
from copath.data.audit import AuditConfig, PrivacyCheckError, main, run_audit
from copath.data.load import DataRootError, resolve_data_root
from copath.data.table_reader import UnsupportedTableFormat, iter_table_chunks

from .conftest import snapshot
from .fixtures import build_fixtures

IDS = set(build_fixtures.PARTICIPANT_IDS)
SENSITIVE_COUNT = re.compile(
    r"^n_(participants|rows|measurements|values|records|with_data|duplicate_rows|numeric_values|"
    r"non_numeric_values|blank_values)"
)
CURRENT_BIO = "Current_Biospecimen_Analysis_Results_01Jan2024"


def read(run, name: str) -> pd.DataFrame:
    return pd.read_csv(run["audit"] / name, dtype=str, keep_default_na=False)


def report_texts(run) -> dict[str, str]:
    return {
        p.name: p.read_text(encoding="utf-8")
        for p in sorted(run["reports"].rglob("*")) if p.suffix in {".csv", ".md", ".json"}
    }


def report_files(audit_dir) -> list[str]:
    return sorted(p.relative_to(audit_dir).as_posix() for p in audit_dir.rglob("*") if p.is_file())


def one(frame: pd.DataFrame, **where) -> pd.Series:
    for column, value in where.items():
        frame = frame[frame[column] == value]
    assert len(frame) == 1, f"expected one row for {where}, found {len(frame)}"
    return frame.iloc[0]


# ---------------------------------------------------------------- archives

def test_zip_inspected_without_extraction_and_sources_unchanged(audit_run):
    assert audit_run["before"] == audit_run["after"]  # same files, sizes, mtimes and hashes
    inventory = read(audit_run, "archive_inventory.csv")
    row = one(inventory, source="download.zip")
    assert row["kind"] == "zip" and row["status"] == "audited"
    assert row["sha256"] == audit_run["before"]["download.zip"][2]
    assert int(row["size_bytes"]) == audit_run["before"]["download.zip"][0]
    # nothing was extracted next to the reports or the interim file
    produced = {p.suffix for p in audit_run["work"].rglob("*") if p.is_file()}
    assert produced <= {".csv", ".md", ".json", ".png", ".parquet"}


def test_nested_zip_is_read_one_level_deep(audit_run):
    tables = read(audit_run, "table_inventory.csv")
    nested = one(tables, member_path="extra/Genetics_bundle.zip!/iu_genetic_consensus_20240101.csv")
    assert nested["modality"] == "genetics" and nested["n_participants"] == "35"
    assert not tables["table_name"].str.contains("too_deep").any()
    members = read(audit_run, "archive_member_inventory.csv")
    deeper = one(members, entry="extra/Genetics_bundle.zip!/deeper.zip")
    assert deeper["file_type"] == "nested_zip" and deeper["audited_as_table"] == "False"


def test_imaging_members_are_only_counted(audit_run):
    members = read(audit_run, "archive_member_inventory.csv")
    imaging = members[(members["source"] == "Imaging.zip") & (members["file_type"] == "imaging")]
    assert set(imaging["entry"]) == {"[aggregate] imaging .dcm", "[aggregate] imaging .nii.gz"}
    assert one(imaging, extension=".dcm")["n_files"] == "6"
    assert not members["entry"].str.contains(r"scan_|DaTSCAN/|T1\.nii").any()  # no per-file imaging paths
    tables = read(audit_run, "table_inventory.csv")
    assert one(tables, table_name="idaSearch_1_15_2024")["granularity"] == "imaging-series"


def test_unsupported_and_broken_files_are_reported_not_fatal(audit_run):
    members = read(audit_run, "archive_member_inventory.csv")
    assert one(members, entry="extra/Genetics_bundle.zip!/Legacy_Table.xls")["file_type"] == "tabular_unsupported"
    assert one(members, entry="docs/notes.txt")["audited_as_table"] == "False"
    errors = read(audit_run, "audit_errors.csv")
    empty = one(errors, member="Empty_Table.csv")
    assert empty["exception_type"] == "EmptyDataError"
    assert list(errors.columns) == ["source", "member", "stage", "exception_type", "location"]  # no message column
    broken = one(read(audit_run, "table_inventory.csv"), table_name="Broken_Lines_15Mar2024")
    assert broken["parse_note"] == "malformed lines skipped"
    assert "Legacy_Table.xls" in (audit_run["audit"] / "audit_summary.md").read_text(encoding="utf-8")


def test_unsupported_format_raises_in_reader():
    with pytest.raises(UnsupportedTableFormat):
        list(iter_table_chunks(io.BytesIO(b"x"), ".xls"))


# ------------------------------------------------------ duplicates/versions

def test_duplicate_and_versioned_tables_detected(audit_run):
    dup = read(audit_run, "duplicate_version_inventory.csv")
    demo = dup[dup["group"] == "DEMOGRAPHICS"]
    assert len(demo) == 2 and set(demo["relation"]) == {"identical content"}
    status = dup[dup["group"] == "PARTICIPANT_STATUS"]
    assert set(status["relation"]) == {"same schema, different row count"}
    preferred = one(status, candidate_preferred_version="True")
    assert preferred["source"] == "download (1).zip" and "date suffix" in preferred["preference_reason"]
    assert set(dup[dup["group"] == "MDS_UPDRS_PART_III"]["relation"]) == {"different schema"}
    family = dup[dup["group_type"] == "Current/Pilot/Deprecated family"]
    assert set(family["version_status"]) == {"current", "pilot"}
    assert not (family["candidate_preferred_version"] == "True").any()
    assert set(dup["decision"]) == {"manual review required; nothing was merged or discarded"}


# ----------------------------------------------------- granularity and keys

@pytest.mark.parametrize("table, expected", [
    ("Participant_Status_15Mar2024", "participant-level"),
    ("Vital_Signs_15Mar2024", "participant-visit"),
    ("MDS-UPDRS_Part_III_01Jan2024", "form/event-level"),
    ("Medical_Conditions_Log_15Mar2024", "form/event-level"),
    (CURRENT_BIO, "participant-visit-test"),
    ("idaSearch_1_15_2024", "imaging-series"),
    ("Code_List_01Jan2024", "reference/dictionary"),
])
def test_table_granularity(audit_run, table, expected):
    assert one(read(audit_run, "table_inventory.csv"), table_name=table)["granularity"] == expected


def test_candidate_key_uniqueness(audit_run):
    keys = read(audit_run, "table_granularity_inventory.csv")
    updrs = keys[keys["table_name"] == "MDS-UPDRS_Part_III_01Jan2024"]
    visit = one(updrs, candidate_key="participant+visit")
    assert visit["is_unique"] == "False" and visit["n_duplicate_rows"] == "10"
    form = one(updrs, candidate_key="participant+visit+form")
    assert form["is_unique"] == "True" and form["is_recommended"] == "True"
    vitals = one(keys, table_name="Vital_Signs_15Mar2024", candidate_key="participant+visit")
    assert vitals["is_unique"] == "True"
    # the same test name is used by two assay projects, so the test alone is not a key
    assert one(keys, table_name=CURRENT_BIO, candidate_key="participant+visit+test")["is_unique"] == "False"
    bio = one(keys, table_name=CURRENT_BIO, candidate_key="participant+visit+test+assay")
    assert bio["is_unique"] == "False" and bio["n_duplicate_rows"] == "<5"  # one repeated measurement, suppressed


# --------------------------------------------------------------- biomarkers

def test_long_format_biomarkers_detected(audit_run):
    tables = read(audit_run, "table_inventory.csv")
    assert one(tables, table_name=CURRENT_BIO)["is_long_format"] == "True"
    assert one(tables, table_name="Vital_Signs_15Mar2024")["is_long_format"] == "False"
    tests = read(audit_run, "biomarker_test_inventory.csv")
    abeta = one(tests, table_name=CURRENT_BIO, test_name="ABeta 1-42")
    assert "Abeta42" in abeta["concept"] and abeta["modality"] == "CSF biomarkers"
    assert abeta["units"] == "pg/mL" and abeta["assay"] == "PROJECTID=125"
    assert abeta["n_participants"] == "30" and abeta["n_measurements"] == "45"
    assert one(tests, test_name="pTau217")["modality"] == "blood/plasma biomarkers"
    assert one(tests, test_name="Rare Analyte X")["n_participants"] == "<5"
    by_event = read(audit_run, "biomarker_test_by_event.csv")
    v04 = one(by_event, table_name=CURRENT_BIO, test_name="ABeta 1-42", event_code="V04")
    assert v04["n_participants"] == "15" and v04["event_class"] == "scheduled follow-up"
    assay = read(audit_run, "biomarker_assay_inventory.csv")
    assert set(assay[assay["concept"] == "AD-like: Abeta42"]["harmonisation_review_needed"]) == {"True"}


def test_special_values_counted_separately_from_missing(audit_run):
    special = read(audit_run, "biomarker_special_values.csv")
    abeta = special[(special["test_name"] == "ABeta 1-42") & (special["table_name"] == CURRENT_BIO)]
    got = {row["token"]: (row["token_class"], row["n_values"]) for _, row in abeta.iterrows()}
    assert got == {
        "<LLOQ": ("below_limit", "6"),
        ">ULOQ": ("above_limit", "<5"),
        "ND": ("not_detected", "5"),
        "-1": ("numeric_sentinel", "5"),
    }
    row = one(read(audit_run, "biomarker_test_inventory.csv"), table_name=CURRENT_BIO, test_name="ABeta 1-42")
    assert row["n_blank_values"] == "<5" and row["n_non_numeric_values"] == "13"
    assert one(special, table_name="MDS-UPDRS_Part_III_01Jan2024", field="NHY")["token"] == "UR"


# ---------------------------------------------------------- events/decoding

def test_event_codes_are_classified_not_merged(audit_run):
    events = read(audit_run, "event_code_inventory.csv")
    classes = dict(zip(events["event_code"], events["event_class"]))
    assert classes["SC"] == "screening" and classes["BL"] == "baseline"
    assert classes["V04"] == "scheduled follow-up" and classes["LOG"] == "form/event code"
    assert classes["P102"] == "unknown" and classes["RACE"] == "unknown"
    assert one(events, table_name="Vital_Signs_15Mar2024", event_code="BL")["decode"] == "Baseline"


def test_dictionaries_detected_and_used(audit_run):
    dictionaries = read(audit_run, "dictionary_inventory.csv")
    assert set(dictionaries["dictionary_kind"]) == {"code_list", "data_dictionary"}
    counts = read(audit_run, "participant_count_inventory.csv")
    pd_row = one(counts, table_name="Participant_Status_15Mar2024", cohort_column="COHORT",
                 cohort_value="1 = Parkinson's Disease")
    assert pd_row["n_participants"] == "35"
    columns = read(audit_run, "column_inventory.csv")
    described = one(columns, table_name="Vital_Signs_15Mar2024", column="SYSSUP")
    assert described["dictionary_description"] == "Supine systolic blood pressure"


# ------------------------------------------------------ modalities/overlap

def test_modalities_overlap_and_candidates(audit_run):
    overlap = read(audit_run, "modality_overlap.csv")
    overlap = overlap[(overlap["universe"] == "participant_status") & (overlap["cohort"] == "ALL")]
    assert one(overlap, kind="requested combination", combination="clinical + cognitive")["n_participants"] == "40"
    four = one(overlap, kind="requested combination", combination="clinical + DAT + CSF + genetics")
    assert four["n_participants"] == "35"  # limited by genetics
    assert one(overlap, kind="single modality", combination="CSF")["n_participants"] == "36"
    candidates = read(audit_run, "candidate_feature_inventory.csv")
    assert {"PD-type", "AD-like", "Vascular-risk", "Genetics"} <= set(candidates["target"])
    dat = candidates[(candidates["concept"] == "DAT-SPECT") & (candidates["status"] == "candidate")]
    assert set(dat["field"]) == {"DATSCAN_CAUDATE_R", "DATSCAN_CAUDATE_L", "DATSCAN_PUTAMEN_R", "DATSCAN_PUTAMEN_L"}
    assert set(candidates["evidence"]) == {"name pattern only; usability not verified"}
    tables = read(audit_run, "table_inventory.csv")
    assert one(tables, table_name="Broken_Lines_15Mar2024")["modality"] == "needs_review"
    keywords = read(audit_run, "text_keyword_inventory.csv")
    assert one(keywords, keyword_group="statin", column="CMTRT")["n_participants"] == "7"
    assert (audit_run["reports"] / "figures" / "audit_modality_upset.png").is_file()


def test_reference_dataset_is_reference_only(audit_run):
    tables = read(audit_run, "table_inventory.csv")
    ref = one(tables, table_name="final_multimodal_dataset")
    assert ref["is_reference_derived"] == "True" and ref["modality"] == "reference-only derived dataset"
    candidates = read(audit_run, "candidate_feature_inventory.csv")
    assert "final_multimodal_dataset" not in set(candidates["table_name"])
    text = (audit_run["audit"] / "reference_dataset_audit.md").read_text(encoding="utf-8")
    assert "`AD_like_label`" in text and "reference only" in text


def test_missingness_by_cohort_flags_association(audit_run):
    frame = read(audit_run, "missingness_by_cohort.csv")
    clinical = frame[(frame["level"] == "modality group") & (frame["item"] == "clinical")]
    assert set(clinical["cohort"]) == {"Healthy Control", "Parkinson's Disease", "Prodromal", "SWEDD"}
    assert set(clinical["availability_strongly_associated_with_cohort"]) == {"True"}
    assert one(clinical, cohort="SWEDD")["n_participants_in_cohort"] == "<5"


# ------------------------------------------------- v1.1: universes/overrides

def test_analytic_universes_by_cohort(audit_run):
    universe = read(audit_run, "analytic_universe.csv")
    got = {(r["universe"], r["cohort"]): r["n_participants"] for _, r in universe.iterrows()}
    assert got[("participant_status", "ALL")] == "60" and got[("participant_status", "PD")] == "35"
    assert got[("participant_status", "HC")] == "15" and got[("participant_status", "SWEDD")] == "<5"
    assert got[("curated_bl", "ALL")] == "45" and got[("curated_bl", "PD")] == "25"
    assert got[("curated_bl", "HC")] == "15" and got[("curated_bl", "Prodromal")] == "5"
    assert got[("curated_bl but not participant_status", "ALL")] == "0"


def test_remote_only_and_adverse_event_tables_are_excluded(audit_run):
    tables = read(audit_run, "table_inventory.csv")
    remote = one(tables, table_name="ST-Direct_Demographics_15Mar2024")
    assert remote["excluded_from_modalities"] == "remote-only (ST-Direct)"
    assert remote["pct_participants_in_participant_status"] == "50.0"
    assert one(tables, table_name="Race_and_Ethnicity_Question_in_myPPMI_15Mar2024")["excluded_from_modalities"] != ""
    adverse = one(tables, table_name="Adverse_Event_Log_15Mar2024")
    assert adverse["modality"] == "other" and adverse["excluded_from_modalities"] == "adverse-event table"
    # remote-only participants do not inflate the totals
    counts = read(audit_run, "participant_count_inventory.csv")
    assert one(counts, scope="all source tables")["n_participants"] == "60"
    modalities = read(audit_run, "modality_inventory.csv")
    assert one(modalities, modality="demographics")["n_participants"] == "50"
    assert modalities["modality"].str.startswith("(excluded)").sum() == 4
    curated = one(tables, table_name="PPMI_Curated_Data_Cut_Public_20240310#20240310")
    assert curated["excluded_from_modalities"] == "curated derived dataset"  # universe only, not a source modality


def test_modality_overrides_and_false_matches(audit_run):
    tables = read(audit_run, "table_inventory.csv")
    fs7 = one(tables, table_name="FS7_ASEG_VOL_15Mar2024")
    assert fs7["modality"] == "MRI/imaging-derived" and fs7["modality_basis"] == "domain override"
    assert one(tables, table_name="Grey_Matter_Volume_15Mar2024")["modality"] == "MRI/imaging-derived"
    diagnosis = one(tables, table_name="Primary_Research_Diagnosis_15Mar2024")
    assert diagnosis["modality"] == "diagnosis" and diagnosis["leakage_table"] == "True"
    candidates = read(audit_run, "candidate_feature_inventory.csv")
    putamen = one(candidates, table_name="FS7_ASEG_VOL_15Mar2024", field="Left_Putamen")
    assert putamen["status"].startswith("excluded:")
    leak = candidates[candidates["table_name"] == "Primary_Research_Diagnosis_15Mar2024"]
    assert len(leak) and set(leak["status"]) == {"leakage: diagnosis table, never a feature"}
    wmh = candidates[(candidates["concept"] == "WMH / vascular MRI") & (candidates["status"] == "candidate")]
    assert set(wmh["field"]) == {"Left_WM_hypointensities", "WM_hypointensities"}  # not cerebellum, not non-WM
    from copath.data import classify
    assert not classify.match_test("CACNA1C diff1 day30") and classify.match_test("HbA1c")


def test_overlap_recomputed_on_baseline_universe_by_cohort(audit_run):
    overlap = read(audit_run, "modality_overlap.csv")
    window = "baseline window (SC or BL)"
    block = overlap[(overlap["universe"] == "curated_bl") & (overlap["window"] == window)]
    everyone = block[block["cohort"] == "ALL"]
    assert one(everyone, kind="single modality", combination="clinical")["n_participants"] == "40"
    assert one(everyone, kind="single modality", combination="DAT")["n_participants"] == "38"  # DAT is at SC
    assert one(everyone, kind="requested combination", combination="clinical + DAT")["n_participants"] == "38"
    assert one(everyone, kind="single modality", combination="vascular/medical history")["n_participants"] == "45"
    assert one(everyone, kind="single modality", combination="clinical")["n_in_universe"] == "45"
    assert set(block["cohort"]) == {"ALL", "PD", "HC", "Prodromal"}
    assert one(block[block["cohort"] == "PD"], kind="single modality", combination="clinical")["n_participants"] == "25"
    figures = {p.name for p in (audit_run["reports"] / "figures").iterdir()}
    assert {"bl_modality_overlap_all.png", "bl_modality_overlap_pd.png", "bl_modality_overlap_hc.png"} <= figures


def test_medical_conditions_vascular_concepts_by_cohort_and_timing(audit_run):
    frame = read(audit_run, "vascular_concept_by_cohort.csv")
    code = frame[(frame["source"] == "Medical_Conditions_Log category code") & frame["concept"].str.contains("MHCAT=106")]
    bl = code[(code["universe"] == "curated_bl") & (code["cohort"] == "ALL")]
    assert one(bl, timing="any time")["n_participants"] == "14"
    assert one(bl, timing="at or before baseline")["n_participants"] == "7"
    status = code[(code["universe"] == "participant_status") & (code["cohort"] == "ALL")]
    assert set(status["timing"]) == {"any time"}  # timing needs the curated baseline date
    assert one(code[(code["universe"] == "curated_bl") & (code["cohort"] == "HC")], timing="any time")["n_participants"] == "<5"
    every = frame[frame["source"] == "Medical_Conditions_Log category (every code)"]
    assert {"MHCAT=106 (Cardiovascular)", "MHCAT=112 (Metabolic/Endocrine)", "MHCAT=116 (Allergy/Immunologic)"} == set(every["concept"])
    drugs = frame[frame["source"].str.contains("medication name") & (frame["universe"] == "curated_bl") & (frame["cohort"] == "ALL")]
    assert one(drugs, concept="hyperlipidaemia", timing="any time")["n_participants"] == "7"
    text = (audit_run["audit"] / "medical_conditions_log_audit.md").read_text(encoding="utf-8")
    assert "`MHCAT`" in text and "Cardiovascular" in text and "## Vascular concepts by cohort" in text


def label_n(audit_run, requirement: str, window: str, cohort: str = "ALL", **extra) -> str:
    frame = read(audit_run, "bl_label_feasibility_by_cohort.csv")
    return one(frame, requirement=requirement, window=window, cohort=cohort, **extra)["n_participants"]


def test_csf_projects_are_reported_separately(audit_run):
    assert label_n(audit_run, "CSF Abeta + pTau at the same BL event, project 125", "BL") == "30"
    assert label_n(audit_run, "CSF Abeta + pTau at the same BL event, project 159", "BL") == "21"
    assert label_n(audit_run, "CSF Abeta + pTau at the same BL event, project 283", "BL") == "18"
    assert label_n(audit_run, "CSF Abeta, project 283", "BL") == "22"  # both spellings of the CSF matrix
    assert label_n(audit_run, "CSF Abeta + pTau pair at BL in both project 159 and project 283", "BL") == "9"
    frame = read(audit_run, "bl_label_feasibility_by_cohort.csv")
    names = one(frame, requirement="CSF Abeta + pTau at the same BL event, project 159", cohort="ALL")
    assert names["tests_or_fields"] == "Abeta: ABeta, ABeta raw; pTau: pTau"
    reference = audit_run["audit"] / "reference"
    mapping = pd.read_csv(reference / "csf_assay_project_map.csv", dtype=str, keep_default_na=False)
    assert set(mapping["project"]) == {"125", "159", "283"}
    assert set(mapping[mapping["test_name"] == "ABeta"]["project"]) == {"159"}
    assert set(mapping[mapping["project"] == "159"]["analyte_family"]) == {
        "Abeta (isoform not stated)", "pTau (isoform not stated)", "total tau"}
    assert set(mapping[mapping["test_name"] == "pTau"]["project"]) == {"125", "159"}  # same name, never pooled
    assert set(mapping["status"]) == {"current"} and set(mapping["project_name"]) >= {"Synthetic CSF reanalysis"}
    assert mapping["other_assay_platform_kit_batch_columns"].str.startswith("none").all()
    overlap = pd.read_csv(reference / "csf_project_overlap_at_bl.csv", dtype=str, keep_default_na=False)
    both = one(overlap, project_a="159", project_b="283", cohort="ALL",
               measure="Abeta + pTau pair at BL in both project 159 and project 283")
    assert both["n_participants"] == "9"


def test_curated_csf_column_provenance(audit_run):
    frame = pd.read_csv(audit_run["audit"] / "reference" / "curated_csf_column_provenance.csv", dtype=str,
                        keep_default_na=False)
    got = dict(zip(frame["variable"], frame["documented_project"]))
    assert got["ABeta"] == "159" and got["ptau"] == "159" and got["IU_ABeta42_CSF"] == "283"
    assert got["tau"] == "provenance not documented"
    assert got["IU_pTau181_CSF"].startswith("provenance not documented")
    assert one(frame, variable="ABeta raw")["biospecimen_projects_with_this_test_name"] == "159"


def test_label_feasibility_at_baseline_by_cohort(audit_run):
    assert label_n(audit_run, "plasma pTau217, project 208", "BL") == "8"
    assert label_n(audit_run, "plasma pTau217, project 292", "BL") == "0"
    assert label_n(audit_run, "plasma pTau217, project 292", "any visit") == "12"  # two spellings of the matrix
    assert label_n(audit_run, "plasma pTau217, curated cut column", "BL") == "6"
    assert label_n(audit_run, "alpha-synuclein SAA status = Positive", "BL") == "15"
    assert label_n(audit_run, "alpha-synuclein SAA status missing", "BL") == "15"
    assert label_n(audit_run, "DAT SBR value, curated cut", "BL") == "33"
    assert label_n(audit_run, "DAT SBR value, core lab", "SC") == "38"
    assert label_n(audit_run, "DAT SBR value, core lab", "BL") == "0"
    assert label_n(audit_run, "supine SBP recorded", "BL") == "40"
    assert label_n(audit_run, "supine SBP and DBP recorded at the same visit", "BL") == "35"
    assert label_n(audit_run, "APOE genotype field", "any visit") == "35"
    assert label_n(audit_run, "MoCA, curated cut column", "BL") == "45"
    assert label_n(audit_run, "CSF Abeta + pTau at the same BL event, project 283", "BL", cohort="PD") == "18"
    frame = read(audit_run, "bl_label_feasibility_by_cohort.csv")
    assert set(frame["cohort"]) == {"ALL", "PD", "HC", "Prodromal"}
    text = (audit_run["audit"] / "target_feasibility_summary.md").read_text(encoding="utf-8")
    assert "## Per-label feasibility at baseline, by cohort" in text and "`WM_hypointensities`" in text


def test_bl_overlap_is_filtered_to_the_baseline_universe(audit_run):
    frame = read(audit_run, "bl_modality_overlap_by_cohort.csv")
    assert set(frame["universe"]) == {"curated_bl"} and set(frame["cohort"]) == {"ALL", "PD", "HC", "Prodromal"}
    everyone = frame[frame["cohort"] == "ALL"]
    singles = everyone[everyone["kind"] == "single modality"]
    assert set(singles["combination"]) == {
        "clinical/motor", "cognitive", "DAT", "MRI (FS7)", "CSF", "plasma", "genetics", "SAA",
        "vascular evidence (vitals/medications)"}
    assert set(singles["n_in_universe"]) == {"45"}  # the 15 clinic and 20 remote participants outside are dropped
    assert one(singles, combination="SAA")["n_participants"] == "30"  # 36 have SAA, only 30 at baseline
    assert one(singles, combination="MRI (FS7)")["n_participants"] == "20"
    assert one(singles, combination="plasma")["n_participants"] == "12"
    assert one(frame[frame["cohort"] == "PD"], kind="single modality", combination="clinical/motor")["n_in_universe"] == "25"
    assert {"pairwise", "requested combination", "exclusive pattern (exactly these modality groups)"} <= set(frame["kind"])
    assert one(everyone, kind="requested combination", combination="clinical/motor + DAT")["n_participants"] == "38"


def test_drug_name_frequency_suppresses_small_cells(audit_run):
    freq = read(audit_run, "medication_drug_name_frequency.csv")
    everyone = freq[freq["cohort"] == "ALL"]
    anti = everyone[everyone["drug_class"] == "antihypertensive"]
    assert one(anti, drug_name="lisinopril")["n_participants_any_time"] == "8"
    assert one(anti, drug_name="amlodipine")["n_participants_any_time"] == "7"
    assert "ramipril" not in set(freq["drug_name"])  # two participants: never named
    rare = anti[anti["drug_name"].str.startswith("<5 other names")]
    assert len(rare) == 1 and rare.iloc[0]["n_participants_any_time"] == "<5"
    assert one(anti, drug_name="(any listed drug in this group)")["n_participants_any_time"] == "15"
    assert one(anti, drug_name="lisinopril")["n_participants_ongoing_at_baseline"] == "<5"
    for column in ("n_participants_any_time", "n_participants_ongoing_at_baseline"):
        assert not freq[column].isin(["1", "2", "3", "4"]).any()
    assert one(freq[freq["cohort"] == "HC"], drug_class="antihypertensive", drug_name="lisinopril")["n_participants_any_time"] == "<5"


def test_flagged_drugs_are_kept_out_of_classes_and_get_indications(audit_run):
    freq = read(audit_run, "medication_drug_name_frequency.csv")
    propranolol = freq[(freq["drug_name"] == "propranolol") & (freq["cohort"] == "ALL")]
    assert len(propranolol) == 1 and propranolol.iloc[0]["kind"] == "flagged: ambiguous or excluded"
    assert propranolol.iloc[0]["n_participants_any_time"] == "8"
    assert "propranolol" not in set(freq[freq["kind"] == "candidate class"]["drug_name"])
    tamsulosin = one(freq, drug_name="tamsulosin", cohort="ALL")  # recorded under a brand name
    assert tamsulosin["n_participants_any_time"] == "5" and tamsulosin["drug_class"].startswith("alpha-blocker")
    flagged = read(audit_run, "medication_flagged_indications.csv")
    text = flagged[(flagged["indication_source"] == "indication text category") & (flagged["cohort"] == "ALL")]
    tremor = one(text, drug_name="propranolol", indication="tremor")
    assert tremor["n_participants"] == "6" and tremor["n_records"] == "6"
    assert one(text, drug_name="propranolol", indication="hypertension")["n_participants"] == "<5"
    assert one(text, drug_name="tamsulosin", indication="prostate/urinary")["n_participants"] == "5"
    midodrine = text[text["drug_name"] == "midodrine"]
    assert set(midodrine["indication"]) == {"orthostatic hypotension", "missing"}  # not classed as hypertension
    assert (flagged["indication_source"] == "indication code").any()
    report = (audit_run["audit"] / "medication_vascular_audit.md").read_text(encoding="utf-8")
    for heading in ("## a. Columns", "## b. Drug-name frequency", "## c. Flagged drugs", "## d. Start/stop dates",
                    "## e. Elevated supine blood pressure"):
        assert heading in report
    assert "Drug-class or ATC code field: **none found**" in report and "`WHODRUG`" in report


def test_medication_dates_and_elevated_blood_pressure(audit_run):
    dates = read(audit_run, "medication_date_usability.csv")
    got = dict(zip(dates["metric"], dates["n_records"]))
    assert got["records of baseline-universe participants"] == "57" and got["stop date usable"] == "5"
    assert got["evaluable: started and stopped before baseline"] == "5"
    assert got["evaluable: started after baseline"] == "20"
    bp = read(audit_run, "supine_bp_elevated_by_cohort.csv")
    everyone = one(bp, cohort="ALL")
    assert everyone["n_measured_at_baseline"] == "40" and everyone["n_elevated"] == "10"
    assert everyone["n_measured_at_screening_because_baseline_missing"] == "<5"
    assert everyone["pct_elevated_of_measured"] == "22.7"
    assert one(bp, cohort="HC")["pct_elevated_of_measured"] == "66.7" and one(bp, cohort="PD")["n_elevated"] == "0"


def test_wmh_check_rejects_cerebellar_white_matter(audit_run, tmp_path):
    coverage = read(audit_run, "fs7_wm_hypointensity_coverage.csv")
    kinds = dict(zip(coverage["field"], coverage["classification"]))
    assert kinds["WM_hypointensities"] == "WM hypointensity" and kinds["Left_WM_hypointensities"] == "WM hypointensity"
    assert kinds["non_WM_hypointensities"].startswith("non-WM hypointensity")
    assert kinds["Left_Cerebellum_White_Matter"].startswith("rejected")
    assert one(coverage, field="WM_hypointensities", cohort="ALL")["n_with_value"] == "20"
    report = (audit_run["audit"] / "fs7_aseg_wm_check.md").read_text(encoding="utf-8")
    assert "`WM_hypointensities`" in report and "No validated WMH" not in report
    assert "FS7_APARC_CTH_15Mar2024" in report and "No hypointensity or white-matter field in this table." in report
    # a download whose only white-matter column is a cerebellar volume has no WMH variable
    root = tmp_path / "data"
    root.mkdir()
    rows = "".join(f"88000{i:02d},BL,{14000 + i}\n" for i in range(1, 11))
    (root / "FS7_ASEG_VOL_01Jan2024.csv").write_text("PATNO,EVENT_ID,Left_Cerebellum_White_Matter\n" + rows, encoding="utf-8")
    run_audit(root, tmp_path / "reports", tmp_path / "interim", AuditConfig(make_figures=False))
    report = (tmp_path / "reports" / "audit" / "fs7_aseg_wm_check.md").read_text(encoding="utf-8")
    assert "No validated WMH / WM-hypointensity variable identified." in report
    candidates = pd.read_csv(tmp_path / "reports" / "audit" / "candidate_feature_inventory.csv", dtype=str)
    assert "WMH / vascular MRI" not in set(candidates["concept"])


def test_reference_exports_and_run_summary(audit_run):
    inventory = read(audit_run, "reference_table_inventory.csv")
    assert len(inventory) == 8 and inventory["status"].str.startswith("exported after identifier check").all()
    reference = audit_run["audit"] / "reference"
    for name in ("Current_Biospecimen_Analysis_Results_Summary_Table_15Mar2024.csv",
                 "PPMI_Curated_Data_Cut_Public_20240310_Information.csv",
                 "PPMI_Curated_Data_Cut_Public_20240310_Data_dictionary.csv",
                 "annotated_dictionary_curated_and_biospecimen.csv", "annotated_dictionary_modules.csv",
                 "csf_assay_project_map.csv", "csf_project_overlap_at_bl.csv", "curated_csf_column_provenance.csv"):
        assert (reference / name).is_file(), name
    summary = pd.read_csv(reference / "Current_Biospecimen_Analysis_Results_Summary_Table_15Mar2024.csv", dtype=str)
    assert list(summary["PROJECTID"]) == ["125", "159", "283", "237"]
    extract = pd.read_csv(reference / "annotated_dictionary_curated_and_biospecimen.csv", dtype=str, keep_default_na=False)
    assert set(extract["ITM_NAME"]) == {"TESTNAME", "TESTVALUE", "fampd"}  # medication and other modules left out
    # the workbook dictionary's continuation rows decode the right variable
    values = read(audit_run, "column_value_inventory.csv")
    assert one(values, column="fampd", value="2")["decode"] == "No family history"
    text = (audit_run["audit"] / "audit_summary.md").read_text(encoding="utf-8")
    assert "## Phase 1.5 outputs" in text and "`vascular_concept_by_cohort.csv`" in text
    assert "not produced" not in text
    assert not (audit_run["audit"] / "baseline_feasibility_by_cohort.csv").exists()


def test_reference_table_identifier_check():
    ids = ["3001", "3002", "3003", "3004", "40001"]
    counts = pd.DataFrame({"PROJECTID": ["125", "283", "237"], "UNIQUE_SUBJECT_COUNT": ["3001", "1914", "888"]})
    assert privacy.reference_table_issue(counts, ids) == ""  # one count coinciding with an id is tolerated
    id_column = pd.DataFrame({"X": ["3001", "3002", "3003", "7"], "Y": ["a", "b", "c", "d"]})
    assert "identifier column" in privacy.reference_table_issue(id_column, ids)
    note = pd.DataFrame({"Revision Notes": ["PATNO 40001 removed in 2024", "nothing else"]})
    assert "contains a participant identifier" in privacy.reference_table_issue(note, ids)
    count = pd.DataFrame({"Revision Notes": ["3001 participants were included, cut-off 45000", "nothing else"]})
    assert privacy.reference_table_check(count, ids) == ("", 1)  # a bare number is a coincidence, and is counted
    kept, status, _ = privacy.vet_reference_table(note, ids)
    assert list(kept["Revision Notes"]) == ["nothing else"] and "1 row(s) withheld" in status
    year = pd.DataFrame({"Revision Notes": ["released in 2024", "updated"]})
    assert privacy.reference_table_issue(year, ["2024", "40001"]) == ""  # a year is not treated as an identifier
    header = pd.DataFrame({"3001": ["x"]})
    assert "header" in privacy.reference_table_issue(header, ids)
    assert "3001" not in privacy.reference_table_issue(id_column, ids)


def test_month_index_parses_ppmi_date_formats():
    from copath.data.summarize import month_index

    got = month_index(pd.Series(["03/2031", "2031-03-15", "2031-03-01 00:00:00", "Mar2031", "2031", "", "n/a"]))
    assert list(got[:4]) == [2031 * 12 + 3] * 4 and got[4] == 2031 * 12 + 1
    assert got[5:].isna().all()


# ------------------------------------------------------------------ privacy

def test_suppress_and_safe_pct():
    assert privacy.suppress(0) == 0 and privacy.suppress(5) == 5
    assert privacy.suppress(1) == "<5" and privacy.suppress(4) == "<5"
    assert privacy.suppress(9, threshold=10) == "<10"
    assert privacy.safe_pct(50, 100) == 50.0
    assert privacy.safe_pct(3, 100) == "suppressed" and privacy.safe_pct(98, 100) == "suppressed"
    assert privacy.safe_pct(0, 100) == 0.0 and privacy.safe_pct(1, 0) == ""


def test_no_small_cells_in_reports(audit_run):
    checked = 0
    for path in sorted(audit_run["audit"].glob("*.csv")):
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        for column in frame.columns:
            if SENSITIVE_COUNT.match(column):
                checked += 1
                small = frame[frame[column].isin(["1", "2", "3", "4"])]
                assert small.empty, f"unsuppressed small count in {path.name}:{column}"
    assert checked > 20
    counts = read(audit_run, "participant_count_inventory.csv")
    swedd = one(counts, table_name="Participant_Status_15Mar2024", cohort_column="COHORT_DEFINITION",
                cohort_value="SWEDD")
    assert swedd["n_participants"] == "<5"


def test_no_participant_ids_rows_dates_or_free_text_in_reports(audit_run):
    texts = report_texts(audit_run)
    assert len(texts) >= 20
    for name, text in texts.items():
        assert not any(pid in text for pid in IDS), f"participant id in {name}"
        assert build_fixtures.FREE_TEXT_MARKER not in text, f"free text in {name}"
        for marker in build_fixtures.DATE_MARKERS:
            assert marker not in text, f"participant date in {name}"
    assert privacy.scan_reports_for_ids(audit_run["reports"], IDS) == []


def test_participant_level_table_goes_only_to_interim(audit_run):
    interim = pd.read_parquet(audit_run["result"]["interim_file"])
    assert audit_run["result"]["interim_file"].parent == audit_run["interim"]
    assert set(interim["participant_id"]) == set(build_fixtures.CLINIC_IDS)  # remote-only participants excluded
    assert {"has_clinical", "has_csf", "cohort", "in_participant_status", "in_curated_bl"} <= set(interim.columns)
    assert int(interim["in_curated_bl"].sum()) == 45
    assert not list(audit_run["reports"].rglob("*.parquet"))


def test_privacy_self_check_deletes_reports_on_leak(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    rows = "".join(f"99000{i:02d},BL,1\n" for i in range(1, 11))
    (root / "Leaky_Table.csv").write_text("PATNO,EVENT_ID,9900001\n" + rows, encoding="utf-8")
    with pytest.raises(PrivacyCheckError) as caught:
        run_audit(root, tmp_path / "reports", tmp_path / "interim", AuditConfig())
    assert "9900001" not in str(caught.value)
    assert not [p for p in (tmp_path / "reports").rglob("*") if p.is_file()]
    assert not (tmp_path / "interim").exists()


def test_scanner_ignores_counts_but_finds_ids(tmp_path):
    (tmp_path / "a.csv").write_text("table_name,n_participants\nDemo,9900001\n", encoding="utf-8")
    assert privacy.scan_reports_for_ids(tmp_path, IDS) == []  # a count that happens to equal an id
    (tmp_path / "b.csv").write_text("table_name,n_participants\nscan 9900001,12\n", encoding="utf-8")
    (tmp_path / "c.md").write_text("Table `x 9900002` has 9900003 rows\n", encoding="utf-8")
    found = privacy.scan_reports_for_ids(tmp_path, IDS)
    assert {(f["file"], f["n_matches"]) for f in found} == {("b.csv", 1), ("c.md", 1)}
    assert all("99000" not in json.dumps(f) for f in found)
    assert privacy.checkable_ids(["12", "3001", ""]) == ({"3001"}, 1)


# --------------------------------------------------- reproducibility/config

def test_deterministic_output(audit_run, synthetic_root, tmp_path):
    run_audit(synthetic_root, tmp_path / "reports", tmp_path / "interim", AuditConfig())
    first, second = audit_run["audit"], tmp_path / "reports" / "audit"
    names = report_files(first)
    assert names == report_files(second) and any(n.startswith("reference/") for n in names)
    for name in names:
        if name != "audit_manifest.json":
            assert (first / name).read_bytes() == (second / name).read_bytes(), name
    a = json.loads((first / "audit_manifest.json").read_text(encoding="utf-8"))
    b = json.loads((second / "audit_manifest.json").read_text(encoding="utf-8"))
    assert a["run_id"] == b["run_id"]
    del a["audit_timestamp_utc"], b["audit_timestamp_utc"]
    assert a == b


def test_chunked_reading_gives_identical_reports(audit_run, synthetic_root, tmp_path):
    run_audit(synthetic_root, tmp_path / "reports", tmp_path / "interim", AuditConfig(chunk_rows=7))
    for name in report_files(audit_run["audit"]):
        if name != "audit_manifest.json":
            assert (audit_run["audit"] / name).read_bytes() == (tmp_path / "reports" / "audit" / name).read_bytes(), name


def test_manifest_contents(audit_run):
    manifest = json.loads((audit_run["audit"] / "audit_manifest.json").read_text(encoding="utf-8"))
    for key in ("run_id", "audit_timestamp_utc", "audit_version", "git", "python_version",
                "package_versions", "config", "sources"):
        assert key in manifest
    by_name = {s["source"]: s for s in manifest["sources"]}
    assert by_name["download.zip"]["sha256"] == audit_run["before"]["download.zip"][2]
    assert manifest["privacy_self_check"]["n_identifiers_checked"] == 80
    assert manifest["audit_version"] == "1.2.0" and "modality_overrides" in manifest["config"]["domain_overrides"]
    text = json.dumps(manifest)
    assert str(audit_run["root"]) not in text and audit_run["root"].as_posix() not in text


def test_data_root_from_argument_environment_and_dotenv(tmp_path, synthetic_root):
    assert resolve_data_root(synthetic_root) == synthetic_root
    assert resolve_data_root(env={"PPMI_DATA_ROOT": str(synthetic_root)}) == synthetic_root
    dotenv = tmp_path / ".env"
    dotenv.write_text(f'PPMI_DATA_ROOT="{synthetic_root.as_posix()}"\n', encoding="utf-8")
    assert resolve_data_root(env={}, dotenv_paths=(dotenv,)) == synthetic_root
    with pytest.raises(DataRootError):
        resolve_data_root(env={}, dotenv_paths=())
    with pytest.raises(DataRootError):
        resolve_data_root(env={"PPMI_DATA_ROOT": "<path-to-local-PPMI-folder>"})
    with pytest.raises(DataRootError):
        resolve_data_root(env={"PPMI_DATA_ROOT": str(tmp_path / "missing")})
    with pytest.raises(DataRootError):  # .env is ignored when disabled
        resolve_data_root(env={"COPATH_DISABLE_DOTENV": "1"}, dotenv_paths=(dotenv,))


def test_cli_uses_environment_and_config(tmp_path, synthetic_root, monkeypatch):
    config = tmp_path / "audit.yaml"
    config.write_text("skip_archives: ['Imaging*.zip']\nmake_figures: false\nhash_archives: false\n", encoding="utf-8")
    monkeypatch.setenv("PPMI_DATA_ROOT", str(synthetic_root))
    code = main(["--config", str(config), "--reports-dir", str(tmp_path / "reports"),
                 "--interim-dir", str(tmp_path / "interim"), "--max-rows-per-table", "20"])
    assert code == 0
    audit = tmp_path / "reports" / "audit"
    inventory = pd.read_csv(audit / "archive_inventory.csv", dtype=str, keep_default_na=False)
    skipped = one(inventory, source="Imaging.zip")
    assert skipped["status"] == "skipped" and skipped["sha256"] == ""
    tables = pd.read_csv(audit / "table_inventory.csv", dtype=str, keep_default_na=False)
    assert "idaSearch_1_15_2024" not in set(tables["table_name"])
    limited = one(tables, table_name="Vital_Signs_15Mar2024")
    assert limited["n_rows"] == "20" and limited["row_limit_applied"] == "True"
    assert not (tmp_path / "reports" / "figures").exists()


def test_cli_fails_cleanly_without_data_root(tmp_path, capsys):
    assert main(["--reports-dir", str(tmp_path / "reports"), "--interim-dir", str(tmp_path / "interim")]) == 2
    assert "PPMI_DATA_ROOT" in capsys.readouterr().err
    assert not (tmp_path / "reports").exists()


def test_outputs_must_be_outside_the_data_root(synthetic_root):
    before = snapshot(synthetic_root)
    with pytest.raises(DataRootError):
        run_audit(synthetic_root, synthetic_root / "reports", synthetic_root / "interim", AuditConfig())
    assert snapshot(synthetic_root) == before


def test_member_listing_matches_zipfile(synthetic_root):
    info = archive.inspect_source(synthetic_root, synthetic_root / "download.zip")
    assert info.kind == "zip" and len(info.sha256) == 64
    paths = {m.display_path for m in info.members}
    assert "Participant_Status_01Jan2024.csv" in paths
    assert "extra/Genetics_bundle.zip!/iu_genetic_consensus_20240101.csv" in paths
    assert not any("too_deep" in p for p in paths)
