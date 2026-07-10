# Source Gate

The first action is bundle validation. The second action is source status
construction.

## Bundle Status Mapping

| Bundle status and artifacts | Source status |
| --- | --- |
| `material_acquired` + primary artifact | `source_confirmed` |
| `partial_material_acquired` + partial primary artifact | `source_partial` |
| `metadata_only` | `secondary_only` or `degraded_report_only` |
| `secondary_only` | `secondary_only` |
| `blocked` | `source_blocked` |
| `failed` | `source_failed` |
| `unsupported` | `degraded_report_only` |

Only transcript, subtitle, ASR transcript, authorized local audio-derived
transcript, or task-primary page text can open a normal analysis path.

## Gate Fields

`source_status.json` must preserve:

- `source_status`
- `primary_material_available`
- `can_enter_full_decomposition`
- `can_enter_document_composer`
- `allowed_report_type`
- `source_classes`
- `status_reason`
- `next_step`

`metadata_only`, `secondary_only`, `source_blocked`, `source_failed`, and
`degraded_report_only` must not create full decomposition directories or packs.
