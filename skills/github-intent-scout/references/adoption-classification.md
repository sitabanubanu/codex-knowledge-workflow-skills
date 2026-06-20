# Adoption Classification

Use this reference to state what the user should do with each serious candidate now.

## Core Rule

Keep adoption class separate from best use role. Do not stretch a component or reference into a direct recommendation just to have an answer.

## Adoption Classes

| Adoption Class | Meaning | Typical Next Step |
|---|---|---|
| `direct-use` | Meets the user's core need with a clear adoption path. | Try or install it first. |
| `light-adapt` | Mechanism fits, but needs small path, host, config, or prompt edits. | Try after a small adapter/change. |
| `component-use` | Solves a subproblem such as parsing, indexing, conversion, or UI. | Use inside a toolchain or custom skill. |
| `reference-only` | Not worth adopting, but useful to understand the ecosystem or design. | Keep as evidence or handoff material. |
| `near-miss` | Close but misses a decisive user constraint. | Do not prioritize unless constraints change. |
| `exclude` | Misleading, unsupported, stale, unsafe, or wrong category. | Do not use. |

## Best Use Role vs. Adoption Class

- `Best use role` says where the candidate sits in the solution architecture.
- `Adoption Class` says what action the user should take.

Example: a parser library may have best use role `supporting-component` and adoption class `component-use`.

## Smallest Adoption Path

For direct recommendations, include:

```text
adoption:
- command or install path, if verified
- first sample task to try
- expected output
- known blocker or caveat
```

If no candidate reaches `direct-use` or `light-adapt`, say that plainly.

