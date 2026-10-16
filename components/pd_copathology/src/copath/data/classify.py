"""Naming rules used by the audit: column roles, modalities, event codes, candidates.

Every rule here is a naming heuristic. A match says "this looks like X and
should be reviewed", never "this is scientifically usable as X". Where no rule
matches, the result is ``needs_review`` rather than a guess.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

NEEDS_REVIEW = "needs_review"


def norm(name: str) -> str:
    """Upper-case a name and collapse everything non-alphanumeric to ``_``."""
    return re.sub(r"[^A-Z0-9]+", "_", str(name).upper()).strip("_")


# --------------------------------------------------------------------------
# Column roles
# --------------------------------------------------------------------------

_ID_NAMES = [
    "PATNO", "SUBJECT_ID", "SUBJECT", "SUBJID", "SUBJ_ID", "SUBJECTID", "PARTICIPANT_ID",
    "PARTICIPANT", "PATIENT_ID", "PATIENT_NUMBER", "SUBJECT_NUMBER",
]
_VISIT_NAMES = [
    "EVENT_ID", "CLINICAL_EVENT", "VISIT", "VISIT_ID", "VISCODE", "VISIT_NAME", "VISIT_CODE", "EVENT",
]
_COHORT_RE = re.compile(
    r"^(COHORT|COHORT_DEFINITION|APPRDX|CONCOHORT|CONCOHORT_DEFINITION|SUBGROUP|ENROLL_STATUS|"
    r"PRIMDIAG|GROUP|RESEARCH_GROUP|DIAGNOSIS|ENRL[A-Z0-9]+)$"
)
_DATE_NAME_RE = re.compile(
    r"((^|_)DATE|(?<!CAU)DATE($|_)|DT$|ORIG_ENTRY|LAST_UPDATE|UPDATE_STAMP|TIMESTAMP|_STAMP$|_TIME$|^DOB$|BIRTH)"
)
_TEST_NAMES = ["TESTNAME", "TEST_NAME", "LTSTNAME", "ANALYTE", "TEST"]
_VALUE_NAMES = ["TESTVALUE", "TEST_VALUE", "LSIRES", "LUSRES", "RESULT", "VALUE"]
_UNIT_NAMES = ["UNITS", "UNIT", "LSIUNIT", "LUSUNIT"]
_MATRIX_NAMES = ["TYPE", "SAMPLE_TYPE", "SPECIMEN_TYPE", "MATRIX"]
_ASSAY_NAMES = ["PROJECTID", "PROJECT_ID", "ASSAY", "PLATFORM", "KIT", "METHOD"]
_SAMPLE_NAMES = ["SAMPLE_ID", "SAMPLEID", "SPECIMEN_ID", "BARCODE", "ALIQUOT_ID"]
_SERIES_NAMES = ["IMAGE_ID", "IMAGE_DATA_ID", "SERIES_ID", "SERIES_UID", "IMAGEUID", "SCAN_ID", "SERIES"]
_FORM_NAMES = ["PAG_NAME", "PDSTATE", "NUPSOURC"]
_ROWID_NAMES = ["REC_ID", "ROW_ID", "RECORD_ID"]
# Assay attributes of a long-format table that are tracked per test (distinct values only).
_LONG_ATTR_NAMES = ["RUNDATE", "RUN_DATE", "BATCH", "BATCH_ID", "LOT", "PLATE", "PLATE_ID", "PI_INSTITUTION", "LABORATORY"]
_TEXT_NAME_RE = re.compile(r"(COMM|NOTE|TEXT|DESC|SPEC$|OTH|TERM|VERBATIM|TRT$|NAME$|REASON)")

DATE_VALUE_RE = (
    r"^(\d{1,2}[/-]\d{4}|\d{4}[/-]\d{1,2}([/-]\d{1,2})?|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"[A-Za-z]{3,9}[ /-]?\d{4}|\d{1,2}[ -][A-Za-z]{3}[ -]\d{2,4})"
    r"([ T]\d{1,2}:\d{2}(:\d{2}(\.\d+)?)?)?$"
)


@dataclass
class Roles:
    """Columns of one table, grouped by the structural role their name suggests."""

    pid_cols: list[str] = field(default_factory=list)
    visit_cols: list[str] = field(default_factory=list)
    cohort_cols: list[str] = field(default_factory=list)
    date_cols: list[str] = field(default_factory=list)
    text_cols: list[str] = field(default_factory=list)
    form_cols: list[str] = field(default_factory=list)
    assay_cols: list[str] = field(default_factory=list)
    long_attr_cols: list[str] = field(default_factory=list)
    test_col: str | None = None
    value_col: str | None = None
    unit_col: str | None = None
    matrix_col: str | None = None
    sample_col: str | None = None
    series_col: str | None = None
    rowid_col: str | None = None

    @property
    def pid(self) -> str | None:
        return self.pid_cols[0] if self.pid_cols else None

    @property
    def visit(self) -> str | None:
        return self.visit_cols[0] if self.visit_cols else None

    @property
    def is_long(self) -> bool:
        return self.test_col is not None and self.value_col is not None

    def role_of(self, column: str) -> str:
        checks = [
            (self.pid_cols, "participant_id"), (self.visit_cols, "visit_event"),
            (self.cohort_cols, "cohort_diagnosis"), (self.date_cols, "date"),
        ]
        for cols, label in checks:
            if column in cols:
                return label
        singles = {
            self.test_col: "test_name", self.value_col: "test_value", self.unit_col: "unit",
            self.matrix_col: "sample_matrix", self.sample_col: "sample_id",
            self.series_col: "imaging_series_id", self.rowid_col: "row_id",
        }
        if column in singles:
            return singles[column]
        if column in self.assay_cols:
            return "assay"
        if column in self.form_cols:
            return "form_discriminator"
        if column in self.text_cols:
            return "free_text"
        return ""


def _ordered(columns: list[str], names: list[str]) -> list[str]:
    by_norm: dict[str, str] = {}
    for col in columns:
        by_norm.setdefault(norm(col), col)
    return [by_norm[n] for n in names if n in by_norm]


def detect_roles(columns: list[str]) -> Roles:
    roles = Roles()
    roles.pid_cols = _ordered(columns, _ID_NAMES)
    roles.visit_cols = _ordered(columns, _VISIT_NAMES)
    roles.cohort_cols = [c for c in columns if _COHORT_RE.match(norm(c))]
    roles.date_cols = [c for c in columns if _DATE_NAME_RE.search(norm(c))]
    roles.form_cols = _ordered(columns, _FORM_NAMES)
    tests, values = _ordered(columns, _TEST_NAMES), _ordered(columns, _VALUE_NAMES)
    if tests and values:
        roles.test_col, roles.value_col = tests[0], values[0]
        for names, attr in ((_UNIT_NAMES, "unit_col"), (_MATRIX_NAMES, "matrix_col")):
            found = _ordered(columns, names)
            if found:
                setattr(roles, attr, found[0])
        roles.assay_cols = _ordered(columns, _ASSAY_NAMES)
        roles.long_attr_cols = _ordered(columns, _LONG_ATTR_NAMES)
    for names, attr in ((_SAMPLE_NAMES, "sample_col"), (_SERIES_NAMES, "series_col"), (_ROWID_NAMES, "rowid_col")):
        found = _ordered(columns, names)
        if found:
            setattr(roles, attr, found[0])
    taken = set(roles.pid_cols + roles.visit_cols + roles.cohort_cols + roles.date_cols)
    taken |= {roles.test_col, roles.value_col, roles.unit_col, roles.matrix_col}
    roles.text_cols = [c for c in columns if c not in taken and _TEXT_NAME_RE.search(norm(c))]
    return roles


# --------------------------------------------------------------------------
# Table names, versions, dictionaries
# --------------------------------------------------------------------------

_NAME_DATE_RE = re.compile(r"[_\- ]((\d{1,2})([A-Za-z]{3})(\d{4})|(\d{4})(\d{2})(\d{2}))$")
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
_STATUS_RES = [
    ("deprecated", re.compile(r"deprecat|archiv|obsolete|retired", re.I)),
    ("pilot", re.compile(r"(^|[_\- ])pilot([_\- ]|$)", re.I)),
    ("current", re.compile(r"(^|[_\- ])current([_\- ]|$)", re.I)),
]
_DICT_NAME_RE = re.compile(r"code_?list|data_?dictionary|codebook|dictionary", re.I)


def split_table_name(stem: str) -> tuple[str, str]:
    """Split ``Demographics_01Jan2024`` into base name and ISO date suffix (or ``""``)."""
    match = _NAME_DATE_RE.search(stem)
    if not match:
        return stem, ""
    if match.group(2):
        month = _MONTHS.get(match.group(3).lower())
        if not month:
            return stem, ""
        iso = f"{match.group(4)}-{month:02d}-{int(match.group(2)):02d}"
    else:
        iso = f"{match.group(5)}-{match.group(6)}-{match.group(7)}"
    return stem[: match.start()], iso


def version_status(name: str) -> str:
    for label, pattern in _STATUS_RES:
        if pattern.search(name):
            return label
    return "unlabelled"


def family_name(base_name: str) -> str:
    """Base name with Current/Pilot/Deprecated markers removed, for grouping variants."""
    cleaned = re.sub(r"(?i)(deprecated|archived|pilot|current)", "", base_name)
    return norm(cleaned)


def dictionary_kind(table_name: str, columns: list[str]) -> str | None:
    """``"code_list"``, ``"data_dictionary"`` or ``None``."""
    names = {norm(c) for c in columns}
    if {"CODE", "DECODE"} <= names:
        return "code_list"
    if "ITM_NAME" in names and names & {"DSCR", "DESCRIPTION"}:
        return "data_dictionary"
    if _DICT_NAME_RE.search(table_name) and not (names & set(_ID_NAMES)):
        return "data_dictionary"
    return None


# --------------------------------------------------------------------------
# Modalities
# --------------------------------------------------------------------------

DICTIONARY = "dictionary/reference"
MIXED_BIOSPECIMEN = "mixed biospecimen (modality assigned per test)"

# Ordered: the first matching rule gives the modality; later matches are
# recorded so a reviewer can see the ambiguity.
_MODALITY_RULES: list[tuple[str, str, str]] = [
    (DICTIONARY, r"code_list|data_dictionary|codebook|dictionary", ""),
    ("DAT-SPECT", r"datscan|dat_scan|dat_spect|(^|_)spect(_|$)|(^|_)sbr(_|$)", ""),
    ("MRI/imaging-derived",
     r"(^|_)mri(_|$)|magnetic_resonance|(^|_)dti(_|$)|freesurfer|av_?133|(^|_)pet(_|$)|"
     r"gr[ae]y_matter|volumetric|(^|_)wmh(_|$)|white_matter|idasearch|imaging|image_collection", ""),
    ("genetics", r"genetic|genotyp|apoe|consensus|gwas|(^|_)wgs(_|$)|(^|_)prs(_|$)|mutation|variant", ""),
    ("CSF biomarkers", r"(^|_)csf(_|$)|cerebrospinal|(^|_)saa(_|$)|seed_amplification", ""),
    ("blood/plasma biomarkers", r"plasma|serum|blood_biomarker", ""),
    (NEEDS_REVIEW, r"biospecimen_analysis|biospecimen_result", MIXED_BIOSPECIMEN),
    ("cognitive",
     r"montreal|moca|hopkins|hvlt|benton|letter_number|semantic_fluency|symbol_digit|trail_making|"
     r"clock_drawing|lexical_fluency|boston_naming|neuropsych|cogniti", ""),
    ("clinical/motor",
     r"updrs|hoehn|schwab|neurological_exam|motor|gait|tremor|pd_diagnosis_history|"
     r"features_of_parkinsonism|diagnostic_features|rigidity|bradykinesia", ""),
    ("medications", r"medication|ledd|dopaminergic_therapy|concomitant", ""),
    ("vital signs", r"vital_sign", ""),
    ("vascular/metabolic risk", r"vascular|cardio|metabolic|blood_pressure|lipid|glucose", ""),
    ("medical history",
     r"medical_condition|medical_history|family_history|physical_exam|surgery|adverse_event|comorbid", ""),
    ("enrollment/cohort",
     r"participant_status|cohort|enrol|screening|eligib|inclusion|exclusion|conclusion_of_study|"
     r"clinical_diagnosis|consent|randomi", ""),
    ("demographics", r"demograph|socio_economic|age_at_visit|subject_characteristics", ""),
    ("other", r"epworth|rem_sleep|(^|_)rbd(_|$)|scopa|upsit|olfact|smell|depression|(^|_)stai(_|$)|"
              r"(^|_)quip(_|$)|anxiety|sleep", "non-motor clinical scale; assign manually if retained"),
    ("other", r"lumbar_puncture|sample_collection|sample_inventory",
     "biospecimen collection log, not assay results"),
    ("other", r"laboratory|blood_chemistry|hematology|pregnancy",
     "clinical laboratory; possible glucose/lipid source"),
]
_MODALITY_RULES_C = [(m, re.compile(p), d) for m, p, d in _MODALITY_RULES]


def classify_table(table_name: str, column_modalities: list[str]) -> dict[str, object]:
    """Assign a modality from the table name, falling back to column evidence."""
    key = norm(table_name).lower()
    hits = [(m, p.pattern, d) for m, p, d in _MODALITY_RULES_C if p.search(key)]
    if hits:
        modality, pattern, detail = hits[0]
        others = sorted({m for m, _, _ in hits[1:] if m != modality})
        return {
            "modality": modality,
            "modality_basis": "table name rule",
            "modality_detail": detail,
            "also_matched": "; ".join(others),
            "needs_review": modality == NEEDS_REVIEW or bool(others),
        }
    if column_modalities:
        counts: dict[str, int] = {}
        for m in column_modalities:
            counts[m] = counts.get(m, 0) + 1
        best = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        return {
            "modality": best,
            "modality_basis": "column names only (table name unrecognised)",
            "modality_detail": "",
            "also_matched": "; ".join(sorted(set(counts) - {best})),
            "needs_review": True,
        }
    return {
        "modality": NEEDS_REVIEW,
        "modality_basis": "no rule matched",
        "modality_detail": "",
        "also_matched": "",
        "needs_review": True,
    }


def matrix_modality(matrix: str, test_name: str = "") -> str | None:
    """Modality implied by a sample-matrix value such as ``Cerebrospinal Fluid``."""
    text = f"{matrix} {test_name}".lower() if not matrix.strip() else matrix.lower()
    if re.search(r"csf|cerebrospinal", text):
        return "CSF biomarkers"
    if re.search(r"plasma|serum|blood|pbmc", text):
        return "blood/plasma biomarkers"
    if re.search(r"\bdna\b", text):
        return "genetics"
    if matrix.strip():
        return "other"
    return None


# Groups used for the cross-modality overlap.
OVERLAP_GROUPS: dict[str, list[str]] = {
    "clinical": ["clinical/motor"],
    "cognitive": ["cognitive"],
    "DAT": ["DAT-SPECT"],
    "imaging-derived": ["MRI/imaging-derived"],
    "CSF": ["CSF biomarkers"],
    "blood/plasma": ["blood/plasma biomarkers"],
    "genetics": ["genetics"],
    "vascular/medical history": ["medical history", "vascular/metabolic risk", "vital signs"],
}
NAMED_COMBINATIONS: list[list[str]] = [
    ["clinical", "cognitive"],
    ["clinical", "DAT"],
    ["clinical", "CSF"],
    ["clinical", "genetics"],
    ["clinical", "cognitive", "DAT"],
    ["clinical", "cognitive", "CSF"],
    ["clinical", "DAT", "CSF", "genetics"],
]


# --------------------------------------------------------------------------
# Visit / event codes
# --------------------------------------------------------------------------

EVENT_BASIS_CONVENTION = "PPMI naming convention; not verified against the Data User Guide in this run"
EVENT_BASIS_DICT = "decoded by a dictionary table in the download"

_EVENT_PATTERNS: list[tuple[str, str, str]] = [
    (r"^SC$", "screening", ""),
    (r"^RS\d*$", "screening", "re-screening code"),
    (r"^BL$", "baseline", ""),
    (r"^V00$", "unknown", "V00 is not assumed to be baseline"),
    (r"^V\d{2}$", "scheduled follow-up", ""),
    (r"^(ST|PW)$", "unscheduled/special visit", "ST = symptomatic therapy, PW = premature withdrawal"),
    (r"^U[T]?\d+$", "unscheduled/special visit", ""),
    (r"^LOG$", "form/event code", "log-type form record, not a clinic visit"),
    (r"^[RT]\d+$", "unknown", "R##/T## may be remote or telephone contacts; confirm in the Data User Guide"),
    (r"^screening$", "screening", "classified from the label text"),
    (r"^baseline$", "baseline", "classified from the label text"),
    (r"^(month|year|week)\s*\d+$", "scheduled follow-up", "classified from the label text"),
    (r"^unscheduled", "unscheduled/special visit", "classified from the label text"),
]
_DECODE_PATTERNS: list[tuple[str, str]] = [
    (r"re-?screen|screening", "screening"),
    (r"baseline", "baseline"),
    (r"unsched|premature|withdraw|symptomatic", "unscheduled/special visit"),
    (r"consent|transfer|conclusion|administr", "administrative record"),
    (r"\blog\b|form", "form/event code"),
    (r"month|year|visit\s*\d|follow", "scheduled follow-up"),
]


def classify_event(code: str, decode: str = "") -> tuple[str, str, str]:
    """Return ``(event_class, basis, note)`` for an event code. Unknown stays unknown."""
    if decode:
        for pattern, label in _DECODE_PATTERNS:
            if re.search(pattern, decode, re.I):
                return label, EVENT_BASIS_DICT, ""
    for pattern, label, note in _EVENT_PATTERNS:
        if re.match(pattern, code.strip(), re.I):
            return label, EVENT_BASIS_CONVENTION, note
    return "unknown", "no rule matched", ""


# --------------------------------------------------------------------------
# Candidate features
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Rule:
    target: str
    concept: str
    col: str | None = None  # regex on the normalised column name
    test: str | None = None  # regex on the test name (case-insensitive)
    note: str = ""


_S = r"[\s\-_]*"
RULES: list[Rule] = [
    # PD-type
    Rule("PD-type", "diagnostic/cohort status",
         col=r"^(COHORT|COHORT_DEFINITION|APPRDX|CONCOHORT|CONCOHORT_DEFINITION|PRIMDIAG|SUBGROUP|"
             r"ENROLL_STATUS|RESEARCH_GROUP|GROUP|DIAGNOSIS)$",
         note="reference-group variable: target-defining, not a model feature"),
    Rule("PD-type", "enrolment subgroup flag", col=r"^ENRL[A-Z0-9]+$",
         note="recruitment-route flag; likely leaks cohort"),
    Rule("PD-type", "MDS-UPDRS", col=r"^(NP[1-4][A-Z0-9]+|NUPDRS[A-Z0-9_]*|MDS_UPDRS[A-Z0-9_]*|UPDRS[A-Z0-9_]*)$"),
    Rule("PD-type", "Hoehn & Yahr", col=r"^(NHY|HOEHN[A-Z_]*)$"),
    Rule("PD-type", "DAT-SPECT",
         col=r"(DATSCAN|DAT_?SPECT|^SBR|_SBR|(^|_)(CAUDATE|PUTAMEN|STRIATUM)(_|$))",
         note="often part of PD diagnostic work-up; check circularity with the target"),
    Rule("PD-type", "alpha-synuclein SAA", col=r"(^SAA|_SAA|SEED_AMP|RT_?QUIC|ASYN|ALPHA_SYN)",
         test=rf"(\bsaa\b|seed{_S}amplif|rt{_S}quic)"),
    Rule("PD-type", "alpha-synuclein (other assay)", test=rf"(alpha{_S}syn|\ba{_S}syn|asyn|α{_S}syn)"),
    Rule("PD-type", "prodromal indicator",
         col=r"(^UPSIT|HYPOSM|(^|_)RBD|PRODROM|PHENOCNV|^TOTAL_CORRECT$)"),
    # AD-like
    Rule("AD-like", "pTau217", col=r"P_?TAU_?217", test=rf"p{_S}tau{_S}217"),
    Rule("AD-like", "pTau181", col=r"P_?TAU_?181", test=rf"p{_S}tau{_S}181"),
    Rule("AD-like", "pTau (isoform not stated)", col=r"(^|_)P_?TAU$",
         test=rf"^(csf{_S})?(p{_S}tau|phospho[\w\s\-]*tau)$",
         note="isoform not in the name; confirm against assay documentation"),
    Rule("AD-like", "total tau", col=r"((^|_)T_?TAU|TOTAL_TAU|^TAU)$",
         test=rf"^(csf{_S})?(t{_S}tau|total{_S}tau|tau)$"),
    Rule("AD-like", "Abeta42", col=r"(A_?BETA_?(1_?)?42|(^|_)AB_?42|AMYLOID.*42)",
         test=rf"(a{_S}(beta|β|b){_S}(1{_S})?42|amyloid[\w\s\-]*42)"),
    Rule("AD-like", "Abeta40", col=r"(A_?BETA_?(1_?)?40|(^|_)AB_?40)",
         test=rf"(a{_S}(beta|β|b){_S}(1{_S})?40|amyloid[\w\s\-]*40)"),
    Rule("AD-like", "biomarker ratio",
         col=r"((TAU|BETA|AB_?4[02]).*RATIO|RATIO.*(TAU|BETA|AB_?4[02]))",
         test=r"((tau|beta|a[bβ]\s*4[02]).*ratio|ratio.*(tau|beta)|4[02]\s*/.*4[02]|tau\s*/)"),
    Rule("AD-like", "NfL", col=r"(^|_)NFL(_|$)", test=rf"(\bnfl\b|neurofilament|\bnf{_S}l\b)"),
    Rule("AD-like", "GFAP", col=r"(^|_)GFAP(_|$)", test=r"gfap"),
    Rule("AD-like", "MoCA", col=r"^(MCATOT|MOCA[A-Z0-9_]*|MCA[A-Z0-9]+)$"),
    Rule("AD-like", "neuropsychological test",
         col=r"^(HVLT[A-Z0-9_]*|DVT_[A-Z0-9_]+|DVS_[A-Z0-9_]+|JLO_[A-Z0-9_]+|LNS_?[A-Z0-9_]*|"
             r"SDM[A-Z0-9_]*|DVSD_SDM|VLT[A-Z0-9_]+|TMT[A-Z0-9_]*|BNT[A-Z0-9_]*|COGSTATE|COGCAT[A-Z0-9_]*|"
             r"COGDECLN|FNCDTCOG)$"),
    Rule("AD-like", "APOE", col=r"APOE", test=rf"apo{_S}e"),
    # Vascular risk
    Rule("Vascular-risk", "hypertension", col=r"(HYPERTEN|(^|_)HTN(_|$))"),
    Rule("Vascular-risk", "diabetes / prediabetes", col=r"(DIABET|(^|_)DM2?(_|$)|HBA1C)",
         test=r"\bhba1c\b|h(a)?emoglobin\s*a1c|^a1c\b"),
    Rule("Vascular-risk", "hyperlipidaemia / lipids", col=r"(HYPERLIP|CHOLEST|LIPID|(^|_)(LDL|HDL)(_|$)|TRIGLY)",
         test=r"cholest|\bldl\b|\bhdl\b|triglycer"),
    Rule("Vascular-risk", "cardiovascular history",
         col=r"(CARDIO|(^|_)CVD(_|$)|HEART|(^|_)CAD(_|$)|ATRIAL|AFIB|ANGINA|INFARCT)"),
    Rule("Vascular-risk", "cerebrovascular history", col=r"(STROKE|(^|_)TIA(_|$)|CEREBROVASC)"),
    Rule("Vascular-risk", "blood pressure",
         col=r"^(SYSSUP|DIASUP|SYSSTND|DIASTND|SYSSIT|DIASIT|SBP[A-Z0-9_]*|DBP[A-Z0-9_]*|[A-Z0-9_]*BLOOD_PRESSURE[A-Z0-9_]*|"
             r"SYS[A-Z0-9_]*BP|DIA[A-Z0-9_]*BP)$",
         note="measured vital sign; possible proxy for the vascular target"),
    Rule("Vascular-risk", "glucose", col=r"GLUC", test=r"glucose"),
    Rule("Vascular-risk", "BMI / weight / height", col=r"^(BMI|WGTKG|HTCM|WEIGHT[A-Z0-9_]*|HEIGHT[A-Z0-9_]*)$"),
    Rule("Vascular-risk", "WMH / vascular MRI",
         col=r"((^|_)WMH|(?<!NON_)WM_HYPOINT|WHITE_MATTER_(HYPO|HYPER|LESION)|HYPERINT|FAZEKAS|LACUN|MICROBLEED)"),
    # Genetics
    Rule("Genetics", "APOE", col=r"APOE", test=rf"apo{_S}e"),
    Rule("Genetics", "GBA1/GBA", col=r"(^|_)GBA1?(_|$)", test=r"\bgba1?\b"),
    Rule("Genetics", "LRRK2", col=r"LRRK2", test=r"lrrk2"),
    Rule("Genetics", "SNCA", col=r"(^|_)SNCA(_|$)", test=r"\bsnca\b"),
    Rule("Genetics", "other PD gene", col=r"(^|_)(PRKN|PARKIN|PINK1|VPS35|PARK7)(_|$)",
         test=r"\b(prkn|parkin|pink1|vps35|park7)\b"),
    Rule("Genetics", "genetic result (generic)", col=r"(GENOTYPE|MUTATION|PATHVAR|(^|_)VARIANT)"),
]
_RULES_C = [
    (r, re.compile(r.col) if r.col else None, re.compile(r.test, re.I) if r.test else None) for r in RULES
]

CONCEPT_MODALITY = {
    "MDS-UPDRS": "clinical/motor", "Hoehn & Yahr": "clinical/motor", "DAT-SPECT": "DAT-SPECT",
    "MoCA": "cognitive", "neuropsychological test": "cognitive", "blood pressure": "vital signs",
    "BMI / weight / height": "vital signs", "WMH / vascular MRI": "MRI/imaging-derived",
    "diagnostic/cohort status": "enrollment/cohort", "enrolment subgroup flag": "enrollment/cohort",
    "GBA1/GBA": "genetics", "LRRK2": "genetics", "SNCA": "genetics", "other PD gene": "genetics",
}


_AB = r"a[\s_-]*(?:beta|β|b)"


def analyte_family(test_name: str) -> str:
    """Amyloid/tau family of a test name, stating whether the isoform is in the name."""
    text = str(test_name).strip()
    if re.search(r"(?i)dilution|qc[\s_-]*flag|contaminant", text):
        return "other"
    if re.search(rf"(?i)ratio|42[\s_/-]*40|{_AB}[\s_-]*4240", text):
        return "Abeta42/40 ratio"
    if re.search(rf"(?i){_AB}[\s_-]*(?:1[\s_-]*)?40", text):
        return "Abeta40"
    if re.search(rf"(?i){_AB}[\s_-]*(?:1[\s_-]*)?42", text):
        return "Abeta42"
    if re.search(rf"(?i)^(?:csf[\s_-]*)?{_AB}(?:[\s_-]*raw)?$", text):
        return "Abeta (isoform not stated)"
    if re.search(r"(?i)p[\s_-]*tau[\s_-]*217|p217", text):
        return "pTau217"
    if re.search(r"(?i)p[\s_-]*tau[\s_-]*181", text):
        return "pTau181"
    if re.search(r"(?i)^(?:csf[\s_-]*)?p[\s_-]*tau$", text):
        return "pTau (isoform not stated)"
    if re.search(r"(?i)^(?:csf[\s_-]*)?(?:t[\s_-]*tau|total[\s_-]*tau|tau)$", text):
        return "total tau"
    return "other"


def match_column(column: str) -> list[Rule]:
    key = norm(column)
    return [r for r, col_re, _ in _RULES_C if col_re is not None and col_re.search(key)]


def match_test(test_name: str) -> list[Rule]:
    text = str(test_name).strip()
    hits = [r for r, _, test_re in _RULES_C if test_re is not None and test_re.search(text)]
    # A ratio such as "ABeta42/ABeta40" is one concept, not its numerator and denominator.
    if any(r.concept == "biomarker ratio" for r in hits):
        hits = [r for r in hits if r.target != "AD-like" or r.concept == "biomarker ratio"]
    return hits


# Free-text keyword groups counted (aggregate only) in medical-history and
# medication tables.
TEXT_TABLE_RE = re.compile(r"medical_condition|medical_history|medication|concomitant|comorbid", re.I)
TEXT_COLUMN_RE = re.compile(r"(TERM|TRT|DRUG|MED|COND|DIAG|INDC|NAME|DESC|TEXT)")
KEYWORD_GROUPS: dict[str, str] = {
    "hypertension": r"hypertens|high blood pressure",
    "diabetes / prediabetes": r"diabet|prediabet|hyperglyc",
    "hyperlipidaemia": r"hyperlipid|hypercholest|dyslipid|high cholesterol",
    "cardiovascular disease": r"myocardial|coronary|atrial fib|heart failure|angina|cardiomyopath|heart attack",
    "cerebrovascular disease": r"stroke|transient isch|cerebrovasc|\btia\b",
    "antihypertensive medication":
        r"lisinopril|amlodipine|losartan|metoprolol|hydrochlorothiazide|ramipril|valsartan|atenolol|"
        r"enalapril|bisoprolol|candesartan|olmesartan|carvedilol",
    "antidiabetic medication":
        r"metformin|insulin|glipizide|glimepiride|sitagliptin|empagliflozin|liraglutide|semaglutide|pioglitazone",
    "statin": r"statin\b",
}
KEYWORD_RES = {k: re.compile(v, re.I) for k, v in KEYWORD_GROUPS.items()}

# The five vascular concepts counted per cohort. `condition` is matched against
# condition / indication text, `medication` against drug names.
VASCULAR_CONCEPTS: dict[str, dict[str, str]] = {
    "hypertension": {"condition": KEYWORD_GROUPS["hypertension"],
                     "medication": KEYWORD_GROUPS["antihypertensive medication"]},
    "diabetes / prediabetes": {"condition": KEYWORD_GROUPS["diabetes / prediabetes"],
                               "medication": KEYWORD_GROUPS["antidiabetic medication"]},
    "hyperlipidaemia": {"condition": KEYWORD_GROUPS["hyperlipidaemia"], "medication": KEYWORD_GROUPS["statin"]},
    "cardiac disease": {"condition": KEYWORD_GROUPS["cardiovascular disease"], "medication": ""},
    "stroke / TIA": {"condition": KEYWORD_GROUPS["cerebrovascular disease"], "medication": ""},
}

SUSPICIOUS_DERIVED_RE = re.compile(
    r"(TARGET|LABEL|PRED|PROB|SCORE|CLUSTER|RISK|FLAG|DERIVED|_X$|_Y$|^UNNAMED|^INDEX$|^LEVEL_\d)"
)
