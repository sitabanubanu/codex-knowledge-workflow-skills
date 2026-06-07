# Correction Policy

When the user says a conclusion is wrong:

1. Determine whether it is a factual correction, persona correction, missing nuance, or privacy request.
2. Preserve the original evidence in `evidence.md`.
3. Add a correction record with date, user wording, affected claim, and action.
4. Update `self.md` or `persona.md`.
5. If the correction contradicts evidence, write: "User correction overrides prior inference."
6. Reclassify the affected claim:
   - user-confirmed correction -> Confirmed Pattern
   - narrowed but still evidence-backed claim -> Probable Pattern
   - rejected or unsupported claim -> remove from final files and keep only in `evidence.md` as retired inference
7. Update `_review/preview.md` if the correction resolves or changes a pending confirmation question.
8. If the user's correction says the overall direction is shallow, wrong, or not what they meant, rerun Phase 7.5 Core Thread Burn instead of defending the old framework.
9. If the user challenges depth, re-test the core thread against contradictory quotes, principle statements, and cognitive break windows.

Never argue that the user's self-correction is invalid. You may say the earlier inference was based on limited chat evidence.
