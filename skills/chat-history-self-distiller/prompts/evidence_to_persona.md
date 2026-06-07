# Evidence To Persona

Turn sampled chat evidence into `persona.md`.

Persona means executable behavior rules, not personality adjectives.

Before writing persona rules, read `_analysis/core_thread_burn.md` and check `Burn Result`:

- `Core Thread Found`: rules may be organized around the tested thread, while preserving contradictions.
- `Weak Thread`: keep rules local and scene-based; do not make the weak thread a standing rule.
- `No Stable Thread`: write only rules directly supported by repeated evidence or user correction.

Required sections:

1. Speech style
2. Message rhythm
3. Humor and emotional tone
4. Decision pattern
5. Conflict pattern
6. Care and attachment pattern
7. Boundary rules
8. Things to avoid when imitating this person
9. Correction log

Every persona rule should include one of:

- High confidence evidence and `Confirmed Pattern` tier
- Medium confidence evidence with `Probable Pattern` caveat
- User-confirmed correction

Low-confidence rules are `Hypothesis`; keep them in a "Needs confirmation" section and do not present them as stable interaction rules.

Use evidence types:

- Direct Quote
- Keyword Cross Validation
- Sequence Pattern from `_analysis/behavior_patterns.json`
- Statistical Pattern
- Human Inference

For conflict, withdrawal, self-mockery, emotion-to-analysis, or ignored-question patterns, prefer sequence evidence when available.

For worldview or decision rules, prefer `principleStatements` over emotion keywords. A principle statement is stronger evidence for how the person models the world.

Do not convert principle statements directly into stable persona rules without dated support, falsification notes, and confidence labels.

Do not show detector pattern names, regex templates, or raw counts in `persona.md`. Translate internal signals into plain interaction rules supported by dated evidence.

Do not imitate private third-party content. Do not invent memories.
