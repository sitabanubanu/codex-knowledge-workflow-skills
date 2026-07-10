# Claim Map

Document composer claim maps must preserve Source / Inference / Extension.

## Source

Source claims can only come from `primary` or `partial_primary` artifacts that
the source gate admitted.

For partial material, Source claims must stay inside the documented partial
scope.

## Inference

Inference claims must reference accepted Source claims and show the reasoning
bridge.

## Extension

Extension claims cover application, critique, synthesis, outside knowledge, or
downstream use. They must be labeled as beyond the original material.

## Degraded States

When source status is `secondary_only`, `source_blocked`, `source_failed`, or
`degraded_report_only`, do not generate normal Source claims. Metadata, search
snippets, comments, and titles stay background/degraded material.
