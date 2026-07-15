# 2026-07-15 Pilot Limitations

This directory preserves the original evaluation scripts and reports as a
historical engineering pilot. Its headline percentages are not release-grade
A/B claims.

Known limitations include:

- ordinary-arm task text contained semantic hints after explicit gold fields
  were removed;
- workflow search fallback generated and scored some candidate attributes;
- retrieval and ranking were not isolated;
- evidence traceability used different methods and denominators by group;
- timing used different task boundaries;
- live backend availability differed between runs;
- the safety denominator was only ten insufficient-material cases;
- no completed two-reviewer blind semantic evaluation exists;
- generated run outputs under `test_outputs/` are not versioned.

Do not modify the saved pilot numbers to match later product behavior. New
release evidence must be produced by the physically separated `eval/v2`
protocol.
