"""Synthetic PPMI-like download for the Phase 2 tests (cohort, labels, split).

Nothing here is derived from PPMI data. Participant identifiers are
7700001-7700600 (the baseline universe) plus 7709001-7709020, which exist only
in source tables and must never enter the cohort. Visit dates are in 2031.
"""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np

N = 600
COUNTS = {"ALL": 600, "PD": 250, "HC": 120, "Prodromal": 200, "SWEDD": 30}
UNIVERSE_IDS = [str(7700000 + i) for i in range(1, N + 1)]
OUTSIDE_IDS = [str(7709000 + i) for i in range(1, 21)]
FREE_TEXT_MARKER = "SYNTHTEXT"
_STAMP = (2024, 6, 1, 9, 0, 0)


def pid(i: int) -> str:
    return UNIVERSE_IDS[i - 1]


def cohort_code(i: int) -> int:
    return 1 if i <= 250 else 2 if i <= 370 else 4 if i <= 570 else 3


def _csv(header: list[str], rows: list[list[object]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def curated_workbook() -> bytes:
    from openpyxl import Workbook

    rng = np.random.default_rng(7)
    workbook = Workbook()
    info = workbook.active
    info.title = "Information"
    info.append(["Revision Notes"])
    info.append(["Synthetic curated cut for Phase 2 tests"])
    sheet = workbook.create_sheet("20240601")
    sheet.append(["SITE", "PATNO", "COHORT", "subgroup", "EVENT_ID", "visit_date", "age", "SEX", "EDUCYRS", "BMI",
                  "moca", "APOE", "APOE_e4", "abeta", "abeta_LLOD", "abeta_ULOD", "ptau", "ptau_LLOD", "tau", "updrs3_score", "hy",
                  "MIA_PUTAMEN_L", "CSFSAA", "asyn", "ptau217_plasma", "orthostasis", "LEDD", "PDTRTMNT", "upsit",
                  "ess", "PRIMDIAG", "PCTL_BNT"])
    for i in range(1, N + 1):
        code = cohort_code(i)
        has_csf, ad_positive = i % 2 == 0, i % 10 < 3
        abeta = float(rng.normal(600, 60)) if ad_positive else float(rng.normal(1200, 150))
        ptau = float(rng.normal(25, 3)) if ad_positive else float(rng.normal(15, 2))
        if i == 60:
            abeta = 0.0  # invalid: masked
        abeta_cell: object = round(abeta, 1) if has_csf else None
        ptau_cell: object = round(ptau, 2) if has_csf else None
        a_llod, a_ulod, p_llod = (0, 0, 0) if has_csf else (None, None, None)
        if i == 80:
            abeta_cell = "not done"  # non-numeric, no flag: masked
        # As in the curated cut: an out-of-range value is discarded and only its limit flag is kept.
        if has_csf and i % 20 == 0 and i not in (60, 80):
            abeta_cell, a_ulod = None, 1  # ABeta42 at or above the upper limit
        if has_csf and i % 40 == 6:
            ptau_cell, p_llod = None, 1  # p-tau at or below the lower limit
        if i == 46:
            abeta_cell, a_llod = None, 1  # ABeta42 below the lower limit
        if i == 100:
            ptau_cell, p_llod = None, 1  # both values censored
        if i == 90:
            abeta_cell = None  # missing without any flag: masked
        e4 = int(rng.random() < (0.5 if ad_positive else 0.2))
        age = round(float(rng.normal(68 if ad_positive else 62, 7)), 1)
        base = [1 + i % 12, int(pid(i)), code, "Sporadic" if code == 1 else "", "BL", f"{1 + i % 12:02d}/2031", age,
                i % 2, 12 + i % 8, round(float(rng.normal(27, 4)), 1), 30 - (4 if ad_positive else 1) - i % 3,
                "e3/e4" if e4 else "e3/e3", e4, abeta_cell, a_llod, a_ulod, ptau_cell, p_llod,
                round(ptau * 9, 1) if has_csf else None, (20 + i % 15) if code == 1 else i % 4, 2 if code == 1 else 0,
                round(0.6 + (0.0 if code == 1 else 0.8) + i % 5 * 0.02, 2) if i % 4 else None,
                (1 if code == 1 else 0) if i % 5 else None, 1500 + i if i % 2 == 0 else None,
                0.2 + i % 7 * 0.01 if i % 6 == 0 else None, i % 9 == 0 and 1 or 0, 300 if code == 1 and i % 3 == 0 else None,
                1 if code == 1 and i % 3 == 0 else 0, 20 + i % 20, i % 12, 1 if code == 1 else 17,
                "<1" if i % 50 == 0 else 10 + i % 80]
        sheet.append(base)
        if i % 2 == 1:
            follow = list(base)
            follow[4], follow[5] = "V04", f"{1 + i % 12:02d}/2032"
            sheet.append(follow)
    workbook.properties.created = workbook.properties.modified = datetime(2024, 6, 1)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def fs7_aseg() -> bytes:
    rows = [[pid(i), "BL", 1500 + i * 3 + (800 if i % 6 == 0 else 0), 3900 + i % 400, 1500000 + i * 10]
            for i in range(1, N + 1) if i % 3 == 0]
    return _csv(["PATNO", "EVENT_ID", "WM_hypointensities", "Left_Hippocampus", "EstimatedTotalIntraCranialVol"], rows)


def fs7_aparc() -> bytes:
    rows = [[pid(i), "BL", round(2.4 + i % 30 * 0.01, 2), round(2.5 + i % 30 * 0.01, 2)] for i in range(1, N + 1) if i % 3 == 0]
    return _csv(["PATNO", "EVENT_ID", "lh_MeanThickness", "rh_MeanThickness"], rows)


def genetics() -> bytes:
    rows = [[pid(i), "E3/E4" if i % 4 == 0 else "E3/E3", "N409S" if i % 25 == 0 else ("NA" if i % 40 == 0 else "0"),
             "G2019S" if i % 30 == 0 else "0"] for i in range(1, 501)]
    rows += [[other, "E3/E3", "0", "0"] for other in OUTSIDE_IDS]
    return _csv(["PATNO", "APOE", "GBA", "LRRK2"], rows)


def saa() -> bytes:
    rows = []
    for i in range(1, N + 1):
        if i % 5 == 0:
            continue  # no SAA at all
        code = cohort_code(i)
        status = "Positive" if (code == 1 and i % 8) or (code != 1 and i % 6 == 0) else "Negative"
        if i % 37 == 0:
            status = "Inconclusive"
        rows.append([pid(i), "BL", status, "24h"])
        if i % 47 == 0:
            rows.append([pid(i), "BL", "Negative" if status == "Positive" else "Positive", "150h"])  # conflicting at BL
        elif i % 31 == 0:
            rows.append([pid(i), "BL", status, "150h"])  # repeated, same status
        rows.append([pid(i), "V04", "Negative" if status == "Positive" else "Positive", "24h"])  # later visit: ignored
    return _csv(["PATNO", "CLINICAL_EVENT", "SAA_Status", "SAAMethod"], rows)


_BIO = ["PATNO", "CLINICAL_EVENT", "TYPE", "TESTNAME", "TESTVALUE", "UNITS", "PROJECTID"]


def biospecimen() -> bytes:
    rng = np.random.default_rng(11)
    rows = []
    for i in range(1, N + 1):
        if i % 3 == 1:
            continue
        low = i % 4 == 0  # amyloid-positive group: low ABeta42/ABeta40
        ab40 = float(rng.normal(10000, 500))
        ab42 = ab40 * float(np.exp(rng.normal(np.log(0.05 if low else 0.10), 0.08)))
        matrix = "CSF" if i % 50 == 0 else "Cerebrospinal Fluid"
        rows.append([pid(i), "BL", matrix, "ABeta42", round(ab42, 1), "pg/mL", 283])
        rows.append([pid(i), "BL", matrix, "ABeta40", round(ab40, 1), "pg/mL", 283])
        rows.append([pid(i), "BL", matrix, "pTau181", round(float(rng.normal(40, 8)), 1), "pg/mL", 283])
        if i % 60 == 0:
            rows.append([pid(i), "BL", matrix, "ABeta42", round(ab42, 1), "pg/mL", 283])  # repeat: mean is used
        rows.append([pid(i), "V04", matrix, "ABeta42", 1.0, "pg/mL", 283])  # later visit: ignored
        rows.append([pid(i), "BL", "Plasma", "ABeta42", 2.0, "pg/mL", 283])  # plasma: ignored
        rows.append([pid(i), "BL", matrix, "ABeta 1-42", 3.0, "pg/mL", 125])  # Elecsys project: never pooled
    rows.append([pid(2), "BL", "Cerebrospinal Fluid", "pTau181", "<LLOQ", "pg/mL", 283])
    return _csv(_BIO, rows)


def pilot_biospecimen() -> bytes:
    # Would wreck the Lumipulse label if it were ever read.
    rows = [[pid(i), "BL", "Cerebrospinal Fluid", test, 999999, "pg/mL", 283] for i in range(1, N + 1)
            for test in ("ABeta42", "ABeta40")]
    return _csv(_BIO, rows)


def vital_signs() -> bytes:
    rows = []
    for i in range(1, N + 1):
        sbp, dbp = 120 + i % 5 * 8, 75 + i % 4 * 6
        if i % 20:
            rows.append([pid(i), "BL", sbp, dbp])
            if i % 7 == 0:
                rows.append([pid(i), "BL", sbp + 10, dbp + 4])  # second reading: the mean is used
            rows.append([pid(i), "SC", 200, 120])  # screening must not be used when baseline exists
        elif i % 40 == 0:
            rows.append([pid(i), "SC", sbp, dbp])  # screening fallback
    rows += [[other, "BL", 150, 95] for other in OUTSIDE_IDS]
    return _csv(["PATNO", "EVENT_ID", "SYSSUP", "DIASUP"], rows)


def medications() -> bytes:
    rows = []

    def add(i: int, drug: str, start: str, stop: str = "", code: object = "", text: str = "", who: str = "") -> None:
        rows.append([pid(i), "LOG", f"{FREE_TEXT_MARKER} {drug} tablets", who, start, stop, code,
                     f"{FREE_TEXT_MARKER} {text}" if text else ""])

    for i in range(1, N + 1):
        if i % 4 == 1:
            continue  # no medication record at all
        add(i, "vitamin d", "01/2030")
        if i % 6 == 0:
            add(i, "Lisinopril", "03/2029", code=14)
        if i % 9 == 0:
            add(i, "product", "2028", who="ATORVASTATIN")  # year-only start before baseline; name only in WHODRUG
        if i % 15 == 0:
            add(i, "metformin", "05/2030", stop="2031")  # year-only stop in the baseline year: ongoing
        if i % 11 == 0:
            add(i, "propranolol", "01/2030", text="essential tremor")  # conditional, no hypertension indication
        if i % 22 == 0:
            add(i, "metoprolol", "01/2030", code=14)  # conditional with the hypertension code
        if i % 13 == 0:
            add(i, "Flomax", "01/2030", text="hypertension")  # prostate-selective alpha-blocker: never
        if i % 23 == 0:
            add(i, "midodrine", "01/2030", text="hypertension")  # pressor: never
        if i % 17 == 0:
            add(i, "amlodipine", "2031")  # year-only start in the baseline year: ambiguous
        if i % 19 == 0:
            add(i, "losartan", "01/2029", stop="06/2030")  # stopped before baseline
        if i % 29 == 0:
            add(i, "simvastatin", "06/2033")  # started after baseline
        if i % 100 == 20:
            add(i, "rosuvastatin", "01/2030")  # one component, and (for 20) no blood pressure: vascular_v1 undecidable
        if i % 41 == 0:
            add(i, "glipizide", "sometime")  # unparseable start
    rows += [[other, "LOG", "lisinopril", "", "01/2020", "", 14, ""] for other in OUTSIDE_IDS]
    return _csv(["PATNO", "EVENT_ID", "CMTRT", "WHODRUG", "STARTDT", "STOPDT", "CMINDC", "CMINDC_TEXT"], rows)


def build(dest: Path) -> Path:
    """Write the synthetic download to ``dest`` (which must not exist yet) and return it."""
    dest = Path(dest)
    dest.mkdir(parents=True)
    members = {
        "main.zip": [
            ("PPMI_Curated_Data_Cut_Public_20240601.xlsx", curated_workbook()),
            ("FS7_ASEG_VOL_01Jun2024.csv", fs7_aseg()),
            ("FS7_APARC_CTH_01Jun2024.csv", fs7_aparc()),
            ("iu_genetic_consensus_20240601.csv", genetics()),
            ("SAA_Biospecimen_Analysis_Results_01Jun2024.csv", saa()),
            ("Vital_Signs_01Jun2024.csv", vital_signs()),
            ("Concomitant_Medication_Log_01Jun2024.csv", medications()),
        ],
        "biospecimen.zip": [
            ("Current_Biospecimen_Analysis_Results_01Jun2024.csv", biospecimen()),
            ("Current_Biospecimen_Analysis_Results_Summary_Table_01Jun2024.csv",
             _csv(["PROJECTID", "PROJECT_NAME"], [[283, "Synthetic Lumipulse panel"]])),
            ("Pilot_Biospecimen_Analysis_Results_01Jun2024.csv", pilot_biospecimen()),
        ],
    }
    for name, entries in members.items():
        with zipfile.ZipFile(dest / name, "w", zipfile.ZIP_DEFLATED) as zf:
            for member, data in entries:
                zf.writestr(zipfile.ZipInfo(member, date_time=_STAMP), data, compress_type=zipfile.ZIP_DEFLATED)
    return dest
