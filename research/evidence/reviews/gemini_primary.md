`Blackbox_ML_Prototype_v0_7_0.zip` contains **two consecutive iterations** since `v0.5.0`: the fully executed `v0.6.0` release (preserved in `evidence/Blackbox_ML_Prototype_v0_6_0_original.zip` and inherited as the base model) and the new `v0.7.0` context-matched pairwise ranking upgrade.

In both `v0.6.0` and `v0.7.0`, the developers implemented the exact three recommendations from our `v0.5.0` analysis—adding post-date history (`blackbox/outcome_history.py`), an uncensored late-reply auxiliary target (`auxiliary_pair_label`), and $L_1$/Elastic-Net + 4-field signal projection (`blackbox/fitting.py`, `blackbox/ranking.py`). However, **no ML policy beat** `conservative`, and `v0.7.0` exhausted its remaining cumulative wall-clock allowance before running the independent validation and 120-episode final test (`status: blocked / incomplete`).

### 1. Evolution Across `v0.5.0` $\rightarrow$ `v0.6.0` $\rightarrow$ `v0.7.0`

| **Dimension**           | **v0.5.0**                                        | **v0.6.0 (Archived in evidence/)**                                                   | **v0.7.0 (Current Package)**                                             |
| ----------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| **Active Default Mode** | `conservative`                                    | `conservative`                                                                       | `conservative` (`artifacts/deployment.json`)                             |
| **Selected Candidate**  | `hybrid` (rejected 38 vs. 45)                     | `hybrid` (constant head, tied **16 vs. 16**)                                         | `rank_tie` (constant head, tied **8 vs. 8** on pilot)                    |
| **Release & Model ID**  | `basis-logit-67419e7cd92f1ec5`                    | `outcome-v06-229e98ef18c18b1c`                                                       | `ranking-v07-a9679aed59b837de` (`6331d361...`)                           |
| **Training Dataset**    | 192 episodes (14,286 rows, 172 pos)               | **288 episodes (21,367 rows, 224 official / 612 aux pos)**                           | Reuses verified `v0.6` bundle (**0 new collection episodes**)            |
| **Feature Schema**      | `v1`: 49 raw / 76 interaction                     | `v2`: **65 joint / 76 directional** (adds post-date history)                         | `v2` **+ 36-feature clean signal projection (**`RANK_NAMES`**)**         |
| **Estimators & Losses** | $L_2$ Ridge Logit (`identity`, `interactions_v1`) | **Elastic-Net ($L_1 + L_2$),** `compact`**,** `signal_projection`**, hold duration** | **Within-world $\pm 7$-day pairwise ranking contrasts**                  |
| **Core Unit Tests**     | 87 core + 4 leakage                               | 99 core + 4 leakage                                                                  | **108 core + 4 leakage** (`results/tests.json`)                          |
| **Evaluation Status**   | 432/432 complete (`blocked`)                      | 432/432 complete (`blocked`: 16–16 tie)                                              | **Incomplete (**`36/36` **pilot +** `12/12` **subprocess; final unrun)** |

### 2. What Happened in `v0.6.0` (And Why It Tied 16–16)

In `v0.6.0` (`evidence/Blackbox_ML_Prototype_v0_6_0_original.zip`), the team implemented all three structural fixes:

1. **Post-Date History (**`blackbox/outcome_history.py`**)**: Added 8 per-member history trackers (`second_yes_rate`, `second_answer_count`, `second_no_history`, `second_record_count`, `timely_recorded_yes_rate`, `second_response_coverage`, `observed_date_count`, `observed_date_rate`), expanding joint features from 49 to **65**.

2. **Uncensored 40-Day Auxiliary Target (**`blackbox/labels.py`**)**: Added `auxiliary_pair_label` (counting mutual `Yes` second-date intentions even when replies arrived on day 4 or 5) alongside a learned timeliness factor (`0.366450`) and a ridge regression proxy for member lockup duration (`scheduled_hold_label` in `[8, 40]` days). Across 288 training episodes (`21,367` rows), this increased positive training examples nearly $3\times$, from **224 official positives** to **612 auxiliary positives**.

3. **Elastic-Net & Signal Projection (**`blackbox/fitting.py`**,** `blackbox/basis.py`**)**: Added exact smooth-split $L_1 + L_2$ regularization plus `compact` and `signal_projection` (which strips out `emotional_availability`, `space_for_relationship`, and `relocate`).

   - On the `auxiliary` **head** (612 positives), Elastic-Net (`compact`, $L_1 = 2, L_2 = 10$) zeroed out 20 noisy features (`25/45` nonzero) and placed all 4 true simulator fields (`relationship_pace:agree`, `lifestyle:agree`, `conversations:agree`, `relationship_goal:agree`) in its top 5 positive weights.

   - **The** `v0.6.0` **Catch**: On the **official** `joint` **MSMI head** (224 positives, `1.05%` base rate), 6-fold seed-grouped cross-validation found that no feature model beat predicting the flat base rate (`0.059314` log loss), so `joint` **selected** `constant_prevalence` **(**`0/65` **nonzero weights)**.

   - In the 192-episode selection pilot (Seeds `2601–2604`), `conservative` and `hybrid` (using the constant `joint` head) tied at **23 official MSMI pairs**, beating `rate` (**21 pairs**) and `aux_hybrid` (**19 pairs**). The automated selector therefore locked in `hybrid`.

   - Because `hybrid`'s `joint` head had `0/65` nonzero weights, `hybrid` **acted identically to** `conservative` **across all 60 frozen final worlds**, tying **16 vs. 16 MSMI pairs** (`4,265` assignments, `538` acceptances, `420` dates each; `delta = 0.0`, CI `[0.0, 0.0]`).




### 3. What `v0.7.0` Changed: Context-Matched Pairwise Ranking

To overcome `v0.6.0` selecting a zero-weight constant on calibrated probabilities, `v0.7.0` (`blackbox/ranking.py`, `scripts/train_rankers.py`) reformulated training as **within-world pairwise ranking** over the verified `v0.6.0` dataset (`artifacts/datasets/v06_observations.json.gz`):

- **36-Feature Clean Signal Projection (**`RANK_NAMES`**)**: Strips out all `:count:` features and all 3 zero-effect distractor fields (`emotional_availability`, `space_for_relationship`, `relocate`), retaining only the **4 true simulator soft fields** (`12` features), **timing/initial history** (`8` features), and **post-date outcome history** (`16` features).

- **Within-World $\pm 7$-Day Contrasts (**`contrasts()`**)**: Matches each positive introduction with up to 5 negative introductions from the **same world (**`seed, variant`**) within $\pm 7$ assignment days**, training on mirrored feature differences $\pm(x\_{\text{pos}} - x\_{\text{neg}})$:




| **Ranking Head (v0.7.0)**                     | **Contrast Rows** | **Positives Represented** | **Best CV Log Loss (vs. ln2=0.693147)** | **Selected Estimator**             | **Nonzero Weights** |
| --------------------------------------------- | ----------------- | ------------------------- | --------------------------------------- | ---------------------------------- | ------------------- |
| `rank_official` (Official timely MSMI)        | 2,218             | 224                       | `0.693147` (`L2=100` got `0.706536`)    | `constant_prevalence`              | **0 / 36**          |
| `rank_auxiliary` (All mutual `Yes` post-date) | 6,010             | 611                       | `0.669634` (beat $\ln 2$ on all grids)  | `ridge_logistic` **($L_2 = 100$)** | **36 / 36**         |

### 4. Deep Insight: Why `rank_aux` Lost the `v0.7.0` Pilot (The Collinear Zero-Sum Trap)

In the `v0.7.0` Selection Pilot (`results/selection_pilot.json` — Seeds `2903–2904`, 12 worlds, 36 episodes), the three modes recorded:

| **Pilot Mode (Seeds 2903–2904)**             | **Introductions** | **Mutual Acceptances** | **First Dates** | **Official MSMI** | **Auxiliary Mutual Yes** |
| -------------------------------------------- | ----------------- | ---------------------- | --------------- | ----------------- | ------------------------ |
| `conservative`                               | 850               | 100                    | 76              | **8**             | **27**                   |
| `rank_tie` (`rank_official`, 0/36 weights)   | 850               | 100                    | 76              | **8**             | **27**                   |
| `rank_aux` (`rank_auxiliary`, 36/36 weights) | 835               | **103**                | 70              | **5**             | **22**                   |

Why did `rank_aux`—which stripped out the 3 noise fields and trained on 6,010 clean auxiliary contrasts—still drop from **8 MSMI pairs to 5** (and from **27 auxiliary** `Yes` **to 22**)?

Inspecting the learned weights inside `artifacts/releases/6331d361.../model.json` reveals a **collinear zero-sum trap**:

| **rank_auxiliary Soft-Field Weights** | **:agree Weight** | **:disagree Weight** | **:missing Weight** | **Sum (wagree​+wdisagree​+wmissing​)** |
| ------------------------------------- | ----------------- | -------------------- | ------------------- | -------------------------------------- |
| `relationship_goal`                   | `+0.22124`        | `-0.61180`           | `+0.39055`          | `0.00000`                              |
| `relationship_pace`                   | `+0.16626`        | `-0.13634`           | `-0.02992`          | `0.00000`                              |
| `lifestyle`                           | `+0.22866`        | `-0.11888`           | `-0.10978`          | `0.00000`                              |
| `conversations`                       | `+0.09659`        | `-0.10631`           | `+0.00972`          | `0.00000`                              |

1. **Why $w\_{\text{missing}}$ Is Forced to Equal $-(w\_{\text{agree}} + w\_{\text{disagree}})$**:

   For every pair, $\text{agree}\_k + \text{disagree}\_k + \text{missing}\_k \equiv 1$, so for every pairwise contrast difference $\Delta x = x_a - x_b$, $\Delta\text{agree}\_k + \Delta\text{disagree}\_k + \Delta\text{missing}\_k \equiv 0$. Under $L_2$-regularized regression ($\min \frac{\lambda}{2}\Vert{}w\Vert{}\_2^2$), the minimum-norm solution forces the three weights to sum to zero:

   $$w\_{\text{missing}} = -(w\_{\text{agree}} + w\_{\text{disagree}})$$

2. **Why** `relationship_goal:missing` **Became the #1 Positive Weight (**`+0.39055`**)**:

   Because disagreeing on `relationship_goal` heavily destroys both initial acceptance and second-date probability, `relationship_goal:disagree` received a massive negative weight (`-0.61180`), while `relationship_goal:agree` received `+0.22124`. By the zero-sum identity, `relationship_goal:missing` was mechanically pushed to:

   $$w\_{\text{missing}} = -0.22124 - (-0.61180) = \mathbf{+0.39055} > w\_{\text{agree}} (+0.22124)$$

3. **How This Breaks Heuristic Tie-Breaking**:

   When `rank_aux` breaks a 1-point heuristic tie between **Couple A** (known to agree on `relationship_goal` = `+0.22124`, missing `conversations` = `+0.00972` $\rightarrow$ `+0.231`) and **Couple B** (known to agree on `conversations` = `+0.09659`, **unknown/missing** `relationship_goal` **=** `+0.39055` $\rightarrow$ `+0.487`), `rank_aux` **actively prefers the couple with a missing** `relationship_goal` **over the couple known to agree on** `relationship_goal`**!**




### 5. Why `v0.7.0` Is Incomplete & Updated Rating (`8.0 / 10`)

- **Strict Cumulative Budget Accounting (**`results/recovery_run.json`**)**: Because the project enforces a single 120-minute workstation cap across continuation sessions and charged `v0.6.0`'s 96.23 minutes against that cap, only **825.15 seconds (\~13.75 minutes)** remained for `v0.7.0`. After running 108 unit tests, 18 runtime probes, the 36-episode pilot, and 12 subprocess episodes (`6–6` tie), time expired before the 60-episode validation (`3001–3002`) and 120-episode final (`3601–3610`) could run (`not_run_budget`).

- **Rating Breakdown (**`8.0 / 10`**)**:

  - **MLOps & Audit Integrity (**`9.9 / 10`**)**: Refusing to reset the 120-minute clock across sessions, cryptographically verifying the `v0.6.0` observation archive (`288` episodes), and leaving `v0.7.0` explicitly `incomplete` / `blocked` rather than faking a pass is exemplary scientific honesty.

  - **Feature & Target Engineering (**`7.0 / 10`**, up from** `5.5 / 10`**)**: `v0.6.0` and `v0.7.0` successfully isolated the 4 true signal fields, added post-date history, and proved that removing the 3-day reply lottery (`rank_auxiliary`) yields a statistically valid cross-validation signal (`0.6696` vs. `0.6931`).

  - **Game-Level ML Lift (**`5.0 / 10`**)**: Because of the collinear `:missing` weight artifact (`+0.39055 > +0.22124` on `relationship_goal`), `rank_aux` lost the pilot (`5` vs. `8`), while `rank_official` selected a constant (`0/36` weights). Dropping the redundant `:missing` dummy variable (using `:agree` and `:disagree` with `:missing` as the `0` reference baseline) would immediately eliminate the zero-sum distortion.