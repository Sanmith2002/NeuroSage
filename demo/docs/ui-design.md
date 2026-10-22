# Four-screen interaction and design system

Desktop-first scientific dashboard. Persistent brand header: **SAFIRA / Research demonstration**, exact baseline alias and `SYNTHETIC ONLY` badge. Left navigation: Dashboard `/`, Framework `/framework`, Simulation Lab `/lab`, Evidence & Limitations `/evidence`. Route links and browser back/forward preserve selected feature or scenario in query state; only predefined opaque selections, never fixture data.

## Visual system

- Background `#0B1220`, raised surfaces `#142033`, separators `#34455E`, primary text `#F4F7FB`, secondary text `#BDCADB`; cyan accent `#67D5F5`. Verify actual contrast in implementation.
- TRUST: emerald `#69D9AA`, check icon + label; CAUTION: amber `#FFD27A`, alert icon; DEFER: lavender `#C5B3FF`, pause icon; REJECTED: rose `#FF9CAB`, stop icon. These describe research execution, not clinical traffic lights. Neutral gray means unavailable; it never means reassuring evidence.
- System sans stack (Segoe UI first on Windows), monospace only for feature IDs, exact dimension identifiers and source references. Body 16px/1.5, supporting text >=14px, headings 24–32px. No network font requirement.
- Spacing scale 4/8/12/16/24/32px, 8–12px corners, modest borders and minimal shadow. No decorative charts with invented values. Motion is opacity/expansion <=180ms; honor reduced-motion and never animate assumed pipeline progress.
- Shared shell: SkipLink → Header → Navigation → Main → persistent limitation footer. FeatureStageSelector, LifecycleBadge, EvidenceNote, SignalCard, ScenarioCard, RunButton, TraceList, ResultPanel and ErrorNotice are shared components. Maintain visible keyboard focus and logical heading order.

## Dashboard wireframe

```text
Header: SAFIRA | Research demonstration | SYNTHETIC ONLY
Nav | Purpose: post-hoc correctness assessment of an existing classifier
    | [Open framework] [Open simulation lab]
    | Three-component architecture: Framework → trusted demo host → browser
    | Eight feature cards (001–008) with offline/runtime tags
    | Historical software verification | Available synthetic scenarios
    | Limitations: unevaluated policy, no independent/clinical validation
```

Feature click opens Explorer at that stage; scenario card opens Lab selection without running. Historical 839 is labeled source-attributed software verification, beside fresh 45-test result with its different environment. No combined count, accuracy percentage or clinical readiness gauge. Scenario skeletons appear during fetch; error panel supports explicit retry of GET only; zero qualified scenarios produces a clear preparation/unavailable state.

## Framework Explorer wireframe

```text
Eight-stage selector, independently selectable (not a mandatory wizard)
Selected stage: purpose + offline/runtime role
Inputs → internal operation → artifact
Verification | failure/unavailable | previous/next dependencies
Expandable six-family signal cards on 004
Source references + research qualification
```

Use an ordered navigation list with selected link and `aria-current`, not inaccessible click-only SVG nodes. Arrow/Tab navigation follows semantics; stages remain selectable in any order. On desktop selector is horizontal above a two-column detail area; narrow screens use a wrapping list. Pipeline edges communicate dependency, never run completion. Partition grouping and estimator/calibration diagrams follow [feature-guide](feature-guide.md); all diagrams have equivalent prose and label **educational illustration**. Unsupported signals retain distinct text states; no fabricated numeric charts or runtime private values. Source refs display approved repository paths as citations, not download links for fixtures.

## Simulation Lab wireframe

```text
Left: scenario selector        Right: selected scope/purpose/evidence note
Qualified / pending /          RUN SIMULATION (qualified only)
educational-only              persistent lifecycle notice
                              Observed host checks / service outcome
                              Result: TRUST | CAUTION | DEFER
                              or Request REJECTED / execution error
                              Expand safe explanations
```

Selection shows category, synthetic scope, qualification and limitations before RUN. No text input for observations, score sliders, threshold controls or upload. Pending/unsupported categories show why and link to Explorer; no active Run button. Initial state says **No simulation run**.

On RUN: disable selection/Run, announce **Running approved synthetic scenario** and show a spinner, not staged checkmarks. MVP uses one POST, no SSE or fake timers. After response, render only evidence-backed trace entries. Historical cards stay visually separate from observations. TRUST/CAUTION display private frozen processing success without numeric probability. DEFER explains actual readiness reason and says internal substage detail unavailable. REJECTED says **Request rejected — no assessment produced**. Unexpected error says **Execution failed — no assessment available**, with fixed code/request ID, no partial success. 409 busy offers manual retry; timeout never becomes DEFER. Browser cancel/route change clears pending display and ignores stale response; do not claim service cancellation.

Result panel receives discriminated server DTO only. Repeated runs require deliberate click. Scenario change clears prior result so a previous outcome cannot be mistaken for current selection. Explain badges through text rather than color. Announce completion once in an accessible status region; move focus to result heading only for user-triggered completion without disrupting keyboard selection.

## Evidence & Limitations wireframe

```text
Research lifecycle strip: fit → select estimator → calibrate → select policy
                         protected final test remains isolated / not evaluated
Feature completion table, with exact source and qualifications
Historical software verification / fresh Phase 1 checks (separate)
Trust-host limitations | missing independent evaluation
Clinical validity not established | deployment not authorized
```

Completion table distinguishes standalone 006–008 closure records from earlier task/verification completion records; do not silently rewrite old framework docs. Show `SELECTED_UNEVALUATED`, spent selection/calibration evidence and protected final-test isolation. No button to unlock protected data, evaluate or deploy.

## Responsive, loading and accessibility behavior

At >=1280px use 232px sidebar and bounded 1440px content; 768–1279px compact sidebar and stacked Lab detail when needed; <768px header menu with focus-managed dialog and one-column cards. At 360px no page-wide overflow, IDs wrap and diagrams have stacked prose alternatives. Tables may have labeled local scroll regions. Minimum 44px touch targets, semantic buttons, descriptive links and explicit busy/disabled explanations. Error notices stay visible until changed. UI tests cover loading/error/empty/qualified/unavailable states; browser tests verify keyboard flows, reduced motion, responsive layout and contrast checks.
