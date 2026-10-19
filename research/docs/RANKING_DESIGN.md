# v0.8 ranking design

The real v0.7 mismatch was training across heuristic-score levels when inference can only reorder equal-score edges. V0.8 requires equality of the actual seven-field soft-agreement count, not the four-field projected count. It also matches world and a seven-day assignment window, using at most five deterministic recorded negatives per positive, then mirrored differences. Inputs are captured before assignment; unchosen pairs receive no invented labels.

The historical data remains288 collection episodes and 21,367 mature introduced pairs. New collection is zero. Matching eligibility can drop positives with no suitable observed negative, so actual represented-positive counts are exported. Contrasts need not share an endpoint or simultaneous availability; selected-label and survivor biases remain.

Four train-only selected models distinguish official/full 36, auxiliary/full 36, auxiliary/reference32 and auxiliary/reference/no-postdate16. The full/reference comparison changes ordinary ridge regularization; it is not a pure prediction-preserving transform after refitting. Reference agreement may still be negative. A frozen v0.7 auxiliary head supplies an unmatched historical control and is excluded from eligible candidates.

The three one-hot weights have a minimum-norm zero-sum representative under ridge. This does not prove a coding defect. Equivalent reference weights are w_agree-w_missing and w_disagree-w_missing; shifting the intercept preserves logits and the missing/agree ordering. Changing the penalty can change fits. Simply translating history rates by a constant cancels in contrasts; changing their smoothing prior is a different unvalidated hypothesis. A half-smoothed rate does not identify a person with no prior date.

New fits use whole-seed folds, equal-seed contrast loss, fixed ridge/elastic-net options, a constant competitor and unchanged convergence checks. Pilot selection and official game-level evaluation remain distinct. No profile monotonicity, simulator coefficient, hidden preference, world seed or ID is hardcoded into a learned score.
