Digging directly into the 21,367 training observations (`artifacts/datasets/v06_observations.json.gz`), the 3,005 ranking contrast pairs (`blackbox/ranking.py`), the 36 learned weights (`artifacts/releases/6331d361.../model.json`), and the 12-world pilot traces (`results/selection_pilot.json`) reveals **three interacting mathematical mechanisms** that explain why `rank_official` collapsed to zero weights and why `rank_auxiliary` (`rank_aux`) lost the pilot `5 vs. 8` (and `22 vs. 27` on auxiliary mutual `Yes`).

### 1. Mechanism 1: The Collinear Zero-Sum Projection (`w_missing > w_agree`)

In `blackbox/features.py`, every soft trait $k$ is encoded as three mutually exclusive one-hot indicators that always sum to 1:

$$\text{agree}\_k + \text{disagree}\_k + \text{missing}\_k \equiv 1$$

When `blackbox/ranking.py` subtracts a negative pair from a positive pair ($\Delta x = x\_{\text{pos}} - x\_{\text{neg}}$), the three difference columns are strictly collinear:

$$\Delta\text{agree}\_k + \Delta\text{disagree}\_k + \Delta\text{missing}\_k \equiv 0$$

Because `rank_auxiliary` minimizes an $L_2$ ridge penalty ($\frac{\lambda}{2}\Vert{}w\Vert{}\_2^2$ with $\lambda = 100$) over a zero-sum subspace, linear algebra forces the learned weights for every soft trait to sum to zero ($w\_{\text{agree}} + w\_{\text{disagree}} + w\_{\text{missing}} = 0$), which locks $w\_{\text{missing}}$ to:

$$w\_{\text{missing}} = -(w\_{\text{agree}} + w\_{\text{disagree}})$$

Whenever a trait has a much stronger penalty for clashing ($w\_{\text{disagree}} \ll 0$) than bonus for agreeing ($w\_{\text{agree}} > 0$), **the zero-sum constraint mechanically pushes $w\_{\text{missing}}$ above $w\_{\text{agree}}$**:

| **Soft Field in rank_auxiliary** | **w(\:agree)** | **w(\:disagree)** | **w(\:missing)** | **Zero-Sum Check** | **Result in Tie-Breaking**                         |
| -------------------------------- | -------------- | ----------------- | ---------------- | ------------------ | -------------------------------------------------- |
| `relationship_goal`              | `+0.22124`     | `-0.61180`        | `+0.39055`       | `0.00000`          | `missing` **beats** `agree` **by** `+0.16931`**!** |
| `relationship_pace`              | `+0.16626`     | `-0.13634`        | `-0.02992`       | `0.00000`          | Normal (`agree > missing > disagree`)              |
| `lifestyle`                      | `+0.22866`     | `-0.11888`        | `-0.10978`       | `0.00000`          | Normal (`agree > missing > disagree`)              |
| `conversations`                  | `+0.09659`     | `-0.10631`        | `+0.00972`       | `0.00000`          | `missing` gets a positive bonus                    |

Because `relationship_goal:missing` (`+0.39055`) is larger than `relationship_goal:agree` (`+0.22124`), on any 1-point heuristic tie between **Couple A** (agrees on `relationship_goal`, missing `conversations` $\rightarrow +0.2310$) and **Couple B** (agrees on `conversations`, missing `relationship_goal` $\rightarrow +0.4871$), `rank_aux` **chooses the couple whose** `relationship_goal` **is blank over the couple known to agree on** `relationship_goal`.

### 2. Mechanism 2: Why Unstratified Contrasts Favored `:missing` (The Two-Cohort Trap)

across all 21,367 training rows in `v06_observations.json.gz`, known agreement on `relationship_goal` has the highest overall success rate (`3.83%` auxiliary `Yes` vs. `3.02%` for `missing` and `1.53%` for `disagree`). Yet across the **3,005 positive contrast pairs** built by `contrasts()`, the mean feature difference ($\bar{x}\_{\text{pos}} - \bar{x}\_{\text{neg}}$) is higher for `:missing` than for `:agree` on **all four traits**:

| **Soft Field (Across 3,005 Contrasts)** | **Mean Δ(agree)** | **Mean Δ(disagree)** | **Mean Δ(missing)** | **Why Δ(missing)>Δ(agree)**                             |
| --------------------------------------- | ----------------- | -------------------- | ------------------- | ------------------------------------------------------- |
| `relationship_goal`                     | `+0.0506`         | `-0.1368`            | `+0.0862`           | Unstratified contrasts mix Score-0 and Score-1+ cohorts |
| `relationship_pace`                     | `+0.0180`         | `-0.0742`            | `+0.0562`           | Unstratified contrasts mix Score-0 and Score-1+ cohorts |
| `lifestyle`                             | `+0.0236`         | `-0.0629`            | `+0.0393`           | Unstratified contrasts mix Score-0 and Score-1+ cohorts |
| `conversations`                         | `+0.0083`         | `-0.0612`            | `+0.0529`           | Unstratified contrasts mix Score-0 and Score-1+ cohorts |

Inspecting the training logs by collection policy reveals why:

- In `starter/kit.py`, **\~30% of members arrive with complete profiles** (all 7 soft fields known on Day 0), while **\~70% arrive with incomplete profiles** (`90%` of fields blank).

- Under `baseline_greedy` (`5,586` training rows), asking `'constraints'` unlocks the 11 hard fields for the 70% incomplete cohort **while leaving all 7 of their soft fields blank (**`missing = 1`**)**.

- Meanwhile, the 30% complete-profile cohort gets matched on Days 0–2 first. By Days 3–59, the remaining complete-profile pairs who agree on `relationship_goal` (`n = 622`) are **leftover repeat-rejectors who explicitly disagree on \~60% of the other soft traits** (`relationship_pace:disagree = 58.5%`, `lifestyle:disagree = 61.1%`, `conversations:disagree = 59.3%`), yielding only a `0.96%` **MSMI rate (**`3.22%` **aux)**—whereas freshly unlocked incomplete-profile pairs (`missing = 1`, `n = 3,825`) are first-time matches with a 50% chance of secret `relationship_goal` agreement and a `1.57%` **MSMI rate (**`3.82%` **aux)**!

- Because `contrasts()` compares any positive pair against any negative pair within $\pm 7$ days **without requiring both pairs to share the same heuristic score (**`soft`**)**, the ranking head learned to prefer freshly unlocked Score-0 (`missing = 1`) pairs over leftover complete-profile pairs—even though at inference time, `rank_aux` is **only allowed to break ties within the exact same heuristic score**.




### 3. Mechanism 3: Retirement Survivor Bias Inverted the New History Weights

In `v0.6.0`/`v0.7.0`, `blackbox/outcome_history.py` added 8 post-date history features using a Laplace-smoothed formula:

$$\text{second\\\_yes\\\_rate} = \frac{\text{yes} + 1}{\text{answered} + 2}$$

- A person with **no prior dates** has `second_yes_rate = (0 + 1) / (0 + 2) = 0.50`.

- A person who went on a date and **answered** `No` has `second_yes_rate = (0 + 1) / (1 + 2) = 0.333` ($< 0.50$).

- A person who went on a date and **answered** `Yes` has `second_yes_rate = (1 + 1) / (1 + 2) = 0.667` ($> 0.50$).




However, in `starter/kit.py` (line 142), **whenever both partners say** `Yes` **after a date, both permanently retire from the pool (**`pause_after_mutual_interest`**) and never appear in any future introduction**. That creates a severe survivor bias in the 21,367 training rows:

| **Post-Date History Group in Training (n = 21,367)**                | **Row Count** | **Mean Day** | **Official MSMI Rate** | **Auxiliary Yes Rate** | **Learned Weight in rank_auxiliary**             |
| ------------------------------------------------------------------- | ------------- | ------------ | ---------------------- | ---------------------- | ------------------------------------------------ |
| **No Prior Date (**`second_yes_rate == 0.50`**)**                   | 18,870        | Day 17.6     | 1.05%                  | 2.88%                  | Baseline (`0.50`)                                |
| **Prior Date Answered** `No` **(**`second_yes_rate:min < 0.50`**)** | 1,438         | Day 39.7     | **1.25%**              | **3.34%**              | **Rewarded (**`w = -0.07672` **on** `:min`**)**  |
| **Prior One-Sided** `Yes` **(**`second_yes_rate:max > 0.50`**)**    | 1,146         | Day 38.8     | **0.70%**              | **2.18%**              | **Penalized (**`w = -0.03525` **on** `:max`**)** |

- Why did people who answered `No` on a prior date (`0.333`) succeed **53% more often** (`3.34%` vs. `2.18%`) than people with a prior one-sided `Yes` (`0.667`)? Because reaching a date and submitting a `No` response proves the member has both a **high** `bias` (accepted the first intro) and a **high** `response_rate` (answered both surveys), whereas every high-quality mutual `Yes` member was **removed from the pool by retirement**.

- Because `0.333 < 0.50 < 0.667`, the linear model fit a **negative slope** on `outcome:second_yes_rate:min` (`-0.07672`), `outcome:second_yes_rate:max` (`-0.03525`), and `outcome:timely_recorded_yes_rate:min` (`-0.04763`)—**actively penalizing members who said** `Yes` **to a prior date and rewarding members who said** `No`!

- Tracing `Seed 2903 development` day-by-day confirms this: `conservative` and `rank_aux` made **100% identical matches on Days 0–11**, and diverged for the very first time on **Day 12** between two all-missing pairs solely because accumulated history/timing weights broke the tie differently, triggering a 28-pair cascade across the rest of the 60-day episode.




### 4. Exact Three-Line Fix for a Next Iteration

1. **Drop** `:missing` **from** `RANK_NAMES` **(**`blackbox/ranking.py`**)**: Keep only `:agree` and `:disagree` for the 4 signal traits (making `:missing` the `0` reference baseline) so ridge regularization can never push $w\_{\text{missing}}$ above $w\_{\text{agree}}$.

2. **Stratify Contrasts by Equal Heuristic Score (**`blackbox/ranking.py`**)**: In `contrasts()`, add `and a_soft_score == b_soft_score` so the ranker only contrasts pairs that actually tie under the heuristic scorer, preventing Score-0 cohort mixing.

3. **Replace Laplace** `0.50` **Centering on Censored Post-Date Rates (**`blackbox/outcome_history.py`**)**: Separate `observed_date_count` / `second_response_coverage` (which capture high response propensity) from `second_yes_rate` by centering `second_yes_rate` at the empirical survivor mean (`~0.35`) rather than `0.50`.