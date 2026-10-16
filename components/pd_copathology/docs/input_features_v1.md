# Input features, version 1.0

**Contract source.** The v1 inference input contract reflects the raw pre-pipeline feature union of the frozen final model bundle. It is intentionally not identical to the broader modelling-tier candidate feature configuration.

Raw, pre-pipeline feature space accepted by the frozen pipelines. The frozen pipelines decide internally which features reach the estimators (for example a feature that is constant in the training rows is dropped); the caller sends the raw record, never post-transform values. All features are numeric (`number`); absent or null features are allowed and are handled only by the frozen pipeline. Unknown fields are ignored and counted (`n_unrecognised_fields`). A supplied value that is not a number is a validation error naming the field.

Optional metadata fields: `participant_id` (echoed, never a feature) and `cohort` (`PD`, `HC`, `Prodromal`, `SWEDD`; used only for `cohort_in_training_scope`, never a feature).

**Scope of input validation.** Input contract v1 validates presence/missingness and numeric type only. It does not currently validate clinical plausibility, physiological ranges, or feature-specific categorical codes (for example, a binary numeric feature supplied as 7). Out-of-range or implausible numeric inputs are still processed by the frozen models and may produce unreliable probabilities. Clinical-range validation, categorical-code validation, and out-of-distribution assessment are outside the current inference contract and must be handled by the caller, the downstream Clinical Predictive Safety Framework, or a future contract version with explicitly documented ranges.

Features: 300. The table is in the canonical feature order (also stored in `x-feature-order` of `input_schema_v1.json`). Descriptions come only from tracked, non-private documentation; where none exists the entry reads "TBD — student to complete".

| # | Feature | Modality | Type | Used by | Description |
|---|---|---|---|---|---|
| 1 | `age` | demographics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 2 | `age_at_visit` | demographics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 3 | `SEX` | demographics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 4 | `EDUCYRS` | demographics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 5 | `race` | demographics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 6 | `HISPLAT` | demographics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 7 | `ASHKJEW` | demographics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 8 | `AFICBERB` | demographics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 9 | `BASQUE` | demographics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 10 | `fampd` | demographics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 11 | `fampd_bin` | demographics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 12 | `handed` | demographics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 13 | `howlive` | demographics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 14 | `sex_orient` | demographics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 15 | `BMI` | demographics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 16 | `upsit` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 17 | `upsit_pctl` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 18 | `upsit_pctl15` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 19 | `moca` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 20 | `bjlot` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 21 | `DVS_JLO_MSSA` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 22 | `DVS_JLO_MSSAE` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 23 | `clockdraw` | cognition | number | pd_type, vascular_risk | TBD — student to complete |
| 24 | `DVT_CLCKDRAW` | cognition | number | pd_type, vascular_risk | TBD — student to complete |
| 25 | `DVZ_CLCKDRAW` | cognition | number | pd_type, vascular_risk | TBD — student to complete |
| 26 | `hvlt_discrimination` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 27 | `hvlt_immediaterecall` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 28 | `hvlt_retention` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 29 | `HVLTFPRL` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 30 | `HVLTRDLY` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 31 | `HVLTREC` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 32 | `DVT_TOTAL_RECALL` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 33 | `DVT_DELAYED_RECALL` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 34 | `DVT_RETENTION` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 35 | `DVT_RECOG_DISC_INDEX` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 36 | `lexical` | cognition | number | pd_type, vascular_risk | TBD — student to complete |
| 37 | `DVT_FAS` | cognition | number | pd_type, vascular_risk | TBD — student to complete |
| 38 | `DVS_FAS` | cognition | number | pd_type, vascular_risk | TBD — student to complete |
| 39 | `lns` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 40 | `DVS_LNS` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 41 | `MODBNT` | cognition | number | pd_type, vascular_risk | TBD — student to complete |
| 42 | `DVS_BNT` | cognition | number | pd_type, vascular_risk | TBD — student to complete |
| 43 | `PCTL_BNT` | cognition | number | pd_type, vascular_risk | TBD — student to complete |
| 44 | `SDMTOTAL` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 45 | `DVT_SDM` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 46 | `DVSD_SDM` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 47 | `TMT_A` | cognition | number | pd_type, vascular_risk | TBD — student to complete |
| 48 | `TMT_B` | cognition | number | pd_type, vascular_risk | TBD — student to complete |
| 49 | `DVZ_TMTA` | cognition | number | pd_type, vascular_risk | TBD — student to complete |
| 50 | `DVZ_TMTB` | cognition | number | pd_type, vascular_risk | TBD — student to complete |
| 51 | `VLTANIM` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 52 | `DVT_SFTANIM` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 53 | `DVS_SFTANIM` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 54 | `MCI_testscores` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 55 | `cogstate` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 56 | `COG_COMPOSITE_INT` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 57 | `COG_COMPOSITE_EXT` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 58 | `PDAQ27` | non-motor clinical | number | pd_type, vascular_risk | TBD — student to complete |
| 59 | `nqol_cogns` | cognition | number | pd_type, vascular_risk | TBD — student to complete |
| 60 | `nqol_comms` | non-motor clinical | number | pd_type, vascular_risk | TBD — student to complete |
| 61 | `nqol_lefs` | motor | number | pd_type, vascular_risk | TBD — student to complete |
| 62 | `nqol_uefs` | motor | number | pd_type, vascular_risk | TBD — student to complete |
| 63 | `MSEADLG` | motor | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 64 | `quip` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 65 | `quip_any` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 66 | `quip_gamble` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 67 | `quip_sex` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 68 | `quip_buy` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 69 | `quip_eat` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 70 | `quip_hobby` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 71 | `quip_pund` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 72 | `quip_walk` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 73 | `ess` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 74 | `rem` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 75 | `gds` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 76 | `stai` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 77 | `stai_state` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 78 | `stai_trait` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 79 | `scopa` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 80 | `scopa_gi` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 81 | `scopa_ur` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 82 | `scopa_cv` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 83 | `scopa_therm` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 84 | `scopa_pm` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 85 | `scopa_sex` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 86 | `orthostasis` | non-motor clinical | number | pd_type, ad_like | TBD — student to complete |
| 87 | `hy` | motor | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 88 | `NHY` | motor | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 89 | `pigd` | motor | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 90 | `NP1COG` | cognition | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 91 | `NP1HALL` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 92 | `NP1DPRS` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 93 | `NP1ANXS` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 94 | `NP1APAT` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 95 | `NP1DDS` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 96 | `NP1FATG` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 97 | `updrs1_score` | non-motor clinical | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 98 | `updrs2_score` | motor | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 99 | `updrs3_score` | motor | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 100 | `updrs_totscore` | motor | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 101 | `CSFSAA` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 102 | `abeta` | biofluid | number | pd_type, vascular_risk | TBD — student to complete |
| 103 | `tau` | biofluid | number | pd_type, vascular_risk | TBD — student to complete |
| 104 | `ptau` | biofluid | number | pd_type, vascular_risk | TBD — student to complete |
| 105 | `asyn` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 106 | `hemohi` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 107 | `ptau217_plasma` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 108 | `bd_tau_plasma` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 109 | `Lilly_ptau217p` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 110 | `Lilly_ptau217p_LLOD` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 111 | `IU_pTau181_CSF` | biofluid | number | pd_type, vascular_risk | TBD — student to complete |
| 112 | `IU_ABeta40_CSF` | biofluid | number | pd_type, vascular_risk | TBD — student to complete |
| 113 | `IU_ABeta42_CSF` | biofluid | number | pd_type, vascular_risk | TBD — student to complete |
| 114 | `IU_GFAP_plasma_mean` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 115 | `IU_GFAP_plasma_std` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 116 | `IU_NFL_plasma_mean` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 117 | `IU_NFL_plasma_std` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 118 | `C2N_AB40` | biofluid | number | pd_type, vascular_risk | TBD — student to complete |
| 119 | `C2N_AB42` | biofluid | number | pd_type, vascular_risk | TBD — student to complete |
| 120 | `C2N_AB4240` | biofluid | number | pd_type, vascular_risk | TBD — student to complete |
| 121 | `C2N_AB_Contaminant` | biofluid | number | pd_type, vascular_risk | TBD — student to complete |
| 122 | `MTBR_TAU243` | biofluid | number | pd_type, vascular_risk | TBD — student to complete |
| 123 | `MTBR_TAU243_LLOD` | biofluid | number | pd_type, vascular_risk | TBD — student to complete |
| 124 | `MTBR_TAU243_InstErr` | biofluid | number | pd_type, vascular_risk | TBD — student to complete |
| 125 | `Roche_IL_1b_CSF` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 126 | `Roche_IL_6_CSF` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 127 | `Roche_IL_6_CSF_LLOD` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 128 | `Roche_YKL40_CSF` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 129 | `Roche_YKL40_CSF_LLOD` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 130 | `NFL_CSF` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 131 | `NFL_CSF_ULOD` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 132 | `nfl_serum` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 133 | `total_di_18_1_BMP` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 134 | `total_di_22_6_BMP` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 135 | `_2_2__di_22_6_BMP` | biofluid | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 136 | `APOE_e4` | genetics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 137 | `GP2_proxy_PGS` | genetics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 138 | `META5_proxy_PGS` | genetics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 139 | `MIA_LOWPUT_EXPECTED` | DAT | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 140 | `MIA_CAUDATE_L` | DAT | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 141 | `MIA_CAUDATE_R` | DAT | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 142 | `MIA_CAUDATE_BILAT` | DAT | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 143 | `MIA_PUTAMEN_L` | DAT | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 144 | `MIA_PUTAMEN_R` | DAT | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 145 | `MIA_PUTAMEN_BILAT` | DAT | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 146 | `MIA_STRIATUM_L` | DAT | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 147 | `MIA_STRIATUM_R` | DAT | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 148 | `MIA_STRIATUM_BILAT` | DAT | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 149 | `aseg_Left_WM_hypointensities` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 150 | `aseg_Brain_Stem` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 151 | `aseg_Left_non_WM_hypointensities` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 152 | `aseg_Optic_Chiasm` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 153 | `aseg_Right_WM_hypointensities` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 154 | `aseg_BrainSegVol` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 155 | `aseg_Right_Lateral_Ventricle` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 156 | `aseg_CC_Central` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 157 | `aseg_5th_Ventricle` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 158 | `aseg_Right_choroid_plexus` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 159 | `aseg_Right_Cerebellum_White_Matter` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 160 | `aseg_Left_vessel` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 161 | `aseg_Left_Cerebellum_Cortex` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 162 | `aseg_MaskVol_to_eTIV` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 163 | `aseg_MaskVol` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 164 | `aseg_TotalGrayVol` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 165 | `aseg_Left_choroid_plexus` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 166 | `aseg_Right_Inf_Lat_Vent` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 167 | `aseg_Left_Pallidum` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 168 | `aseg_Left_Thalamus` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 169 | `aseg_Right_VentralDC` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 170 | `aseg_rhCortexVol` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 171 | `aseg_Right_non_WM_hypointensities` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 172 | `aseg_BrainSegVol_to_eTIV` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 173 | `aseg_Right_Amygdala` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 174 | `aseg_Left_Amygdala` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 175 | `aseg_EstimatedTotalIntraCranialVol` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 176 | `aseg_4th_Ventricle` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 177 | `aseg_Left_Inf_Lat_Vent` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 178 | `aseg_CortexVol` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 179 | `aseg_Right_Pallidum` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 180 | `aseg_lhCortexVol` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 181 | `aseg_CC_Anterior` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 182 | `aseg_CC_Posterior` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 183 | `aseg_Left_Accumbens_area` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 184 | `aseg_Right_vessel` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 185 | `aseg_Right_Cerebellum_Cortex` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 186 | `aseg_Left_Putamen` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 187 | `aseg_3rd_Ventricle` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 188 | `aseg_non_WM_hypointensities` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 189 | `aseg_Right_Caudate` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 190 | `aseg_CC_Mid_Posterior` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 191 | `aseg_lhSurfaceHoles` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 192 | `aseg_Left_Hippocampus` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 193 | `aseg_Right_Hippocampus` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 194 | `aseg_Left_Caudate` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 195 | `aseg_rhCerebralWhiteMatterVol` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 196 | `aseg_Right_Putamen` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 197 | `aseg_WM_hypointensities` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 198 | `aseg_Right_Accumbens_area` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 199 | `aseg_rhSurfaceHoles` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 200 | `aseg_lhCerebralWhiteMatterVol` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 201 | `aseg_BrainSegVolNotVent` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 202 | `aseg_Left_Cerebellum_White_Matter` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 203 | `aseg_Left_VentralDC` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 204 | `aseg_SupraTentorialVolNotVent` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 205 | `aseg_CC_Mid_Anterior` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 206 | `aseg_SupraTentorialVol` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 207 | `aseg_SubCortGrayVol` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 208 | `aseg_Right_Thalamus` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 209 | `aseg_Left_Lateral_Ventricle` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 210 | `aseg_CSF` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 211 | `aseg_SurfaceHoles` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 212 | `aseg_CerebralWhiteMatterVol` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 213 | `aparc_lh_bankssts` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 214 | `aparc_lh_caudalanteriorcingulate` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 215 | `aparc_lh_caudalmiddlefrontal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 216 | `aparc_lh_cuneus` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 217 | `aparc_lh_entorhinal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 218 | `aparc_lh_fusiform` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 219 | `aparc_lh_inferiorparietal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 220 | `aparc_lh_inferiortemporal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 221 | `aparc_lh_isthmuscingulate` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 222 | `aparc_lh_lateraloccipital` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 223 | `aparc_lh_lateralorbitofrontal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 224 | `aparc_lh_lingual` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 225 | `aparc_lh_medialorbitofrontal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 226 | `aparc_lh_middletemporal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 227 | `aparc_lh_parahippocampal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 228 | `aparc_lh_paracentral` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 229 | `aparc_lh_parsopercularis` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 230 | `aparc_lh_parsorbitalis` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 231 | `aparc_lh_parstriangularis` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 232 | `aparc_lh_pericalcarine` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 233 | `aparc_lh_postcentral` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 234 | `aparc_lh_posteriorcingulate` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 235 | `aparc_lh_precentral` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 236 | `aparc_lh_precuneus` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 237 | `aparc_lh_rostralanteriorcingulate` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 238 | `aparc_lh_rostralmiddlefrontal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 239 | `aparc_lh_superiorfrontal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 240 | `aparc_lh_superiorparietal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 241 | `aparc_lh_superiortemporal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 242 | `aparc_lh_supramarginal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 243 | `aparc_lh_frontalpole` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 244 | `aparc_lh_temporalpole` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 245 | `aparc_lh_transversetemporal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 246 | `aparc_lh_insula` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 247 | `aparc_lh_MeanThickness` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 248 | `aparc_rh_bankssts` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 249 | `aparc_rh_caudalanteriorcingulate` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 250 | `aparc_rh_caudalmiddlefrontal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 251 | `aparc_rh_cuneus` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 252 | `aparc_rh_entorhinal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 253 | `aparc_rh_fusiform` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 254 | `aparc_rh_inferiorparietal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 255 | `aparc_rh_inferiortemporal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 256 | `aparc_rh_isthmuscingulate` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 257 | `aparc_rh_lateraloccipital` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 258 | `aparc_rh_lateralorbitofrontal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 259 | `aparc_rh_lingual` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 260 | `aparc_rh_medialorbitofrontal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 261 | `aparc_rh_middletemporal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 262 | `aparc_rh_parahippocampal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 263 | `aparc_rh_paracentral` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 264 | `aparc_rh_parsopercularis` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 265 | `aparc_rh_parsorbitalis` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 266 | `aparc_rh_parstriangularis` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 267 | `aparc_rh_pericalcarine` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 268 | `aparc_rh_postcentral` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 269 | `aparc_rh_posteriorcingulate` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 270 | `aparc_rh_precentral` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 271 | `aparc_rh_precuneus` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 272 | `aparc_rh_rostralanteriorcingulate` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 273 | `aparc_rh_rostralmiddlefrontal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 274 | `aparc_rh_superiorfrontal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 275 | `aparc_rh_superiorparietal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 276 | `aparc_rh_superiortemporal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 277 | `aparc_rh_supramarginal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 278 | `aparc_rh_frontalpole` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 279 | `aparc_rh_temporalpole` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 280 | `aparc_rh_transversetemporal` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 281 | `aparc_rh_insula` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 282 | `aparc_rh_MeanThickness` | MRI | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 283 | `gba_carrier` | genetics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 284 | `lrrk2_carrier` | genetics | number | pd_type, ad_like, vascular_risk | TBD — student to complete |
| 285 | `lumi_abeta42` | biofluid | number | pd_type, vascular_risk | TBD — student to complete |
| 286 | `lumi_abeta40` | biofluid | number | pd_type, vascular_risk | TBD — student to complete |
| 287 | `lumi_ptau181` | biofluid | number | pd_type, vascular_risk | TBD — student to complete |
| 288 | `lumi_ratio_4240` | biofluid | number | pd_type, vascular_risk | TBD — student to complete |
| 289 | `elecsys_ptau_abeta_ratio` | biofluid | number | pd_type, vascular_risk | TBD — student to complete |
| 290 | `sup_sbp` | vascular evidence | number | pd_type, ad_like | TBD — student to complete |
| 291 | `sup_dbp` | vascular evidence | number | pd_type, ad_like | TBD — student to complete |
| 292 | `htn_bp` | vascular evidence | number | pd_type, ad_like | TBD — student to complete |
| 293 | `htn_med_definite` | vascular evidence | number | pd_type, ad_like | TBD — student to complete |
| 294 | `htn_med_conditional` | vascular evidence | number | pd_type, ad_like | TBD — student to complete |
| 295 | `dm_med` | vascular evidence | number | pd_type, ad_like | TBD — student to complete |
| 296 | `dyslipid_med` | vascular evidence | number | pd_type, ad_like | TBD — student to complete |
| 297 | `comp_htn` | vascular evidence | number | pd_type, ad_like | TBD — student to complete |
| 298 | `comp_dm` | vascular evidence | number | pd_type, ad_like | TBD — student to complete |
| 299 | `comp_dyslip` | vascular evidence | number | pd_type, ad_like | TBD — student to complete |
| 300 | `vascular_component_count` | vascular evidence | number | pd_type, ad_like | TBD — student to complete |
