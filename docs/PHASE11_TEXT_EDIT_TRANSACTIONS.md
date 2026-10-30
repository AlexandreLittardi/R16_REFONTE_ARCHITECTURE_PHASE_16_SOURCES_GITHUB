# Phase 11 - Questionnaire, notes and cable-sizing edit boundaries

## Purpose

Continue phase 10 by migrating the engineering questionnaire and Cabling
text inputs to explicit project Undo/Redo boundaries, while retaining all
schema-v2 JSON fields, calculations, 11 tabs and native vector PDF exports.

## Changes made

1. **Engineering questionnaire Apply** (`mixins/configuration_questionnaire.py`):
   data validation and optional file imports run before the transaction begins.
   A successful Apply invokes `_run_project_edit('project:engineering-questionnaire',
   commit)` exactly once. The existing rollback of an unsuccessful `_apply_document`
   remains; cancelling metadata prompts is still a no-op. Opening the modal
   first closes any active Cabling text transaction.
2. **Project notes** (`mixins/notes_tools.py`): a focus session is one
   `notes:typing` history gesture. Begin on `FocusIn`, *before* editing the Text
   widget, because history reads the widget text directly. Finish on `FocusOut`.
   Typing and periodic fallback history polling cannot split one edit.
3. **DC sizing input fields** (`mixins/notes_tools.py`): one focus session is one
   `cabling:sizing-input` gesture. On `FocusOut`, validate and store the numbers
   before closing the edit gate; malformed input does not alter saved parameters.
4. **Undo/Redo while focus remains in an input** (`mixins/safe_project.py`):
   close any in-progress edit before Undo/Redo, including validation of a DC
   field, and re-arm a focused text field after document restoration. This
   prevents skipping pending typed changes or losing grouping for subsequent
   keystrokes.
5. **Tests:** unit tests for active-edit Undo, focus rearm and invalid input;
   real Tk GUI test for notes, cable sizing, questionnaire Apply and subsequent
   Undo/Redo. No new build files or user project data.

## Verification

- `python -m unittest discover -s tests -q`: **191 tests, all pass** (185 in phase 10).
- `xvfb-run -a python tools/test_phase11_text_questionnaire_gui.py`: pass.
- GUI regressions: architecture, unified navigation, phase 9 pointer
  transactions, phase 10 ribbon/dialog commands, Installation, phase 8
  Installation/Cabling, Diagram, Mounting A/B/C, Mounting full 500-panel
  harness and native vector PDF export all pass.
- `xvfb-run -a python tools/test_project_roundtrip_gui.py <project.json>`:
  a real Frimo input retained 533 panels, 9 zones, 2 cable routing areas and
  32 strings after read/write/readback.
- `python tools/report_mro.py`: 53 method names still have multiple definitions;
  no method override was removed during this phase.

## Deliberately not migrated

- Specialized Mounting and Diagram editor history: independent and tested.
- Legacy edits outside the migrated paths: the 600-ms `_poll_history` fallback
  remains in place until every remaining edit entry point is covered.
- Broad mixin deletion or schema migration, Windows EXE packaging and GitHub
  workflow generation: outside this incremental phase.

## Regression commands

```sh
python -m unittest discover -s tests -q
xvfb-run -a python tools/test_phase11_text_questionnaire_gui.py
xvfb-run -a python tools/test_phase10_ribbon_dialog_gui.py
xvfb-run -a python tools/test_mounting_gui.py
xvfb-run -a python tools/test_project_roundtrip_gui.py /path/to/project.json
```

The GUI validations above were performed under Linux/Xvfb. Native Windows
packaging and behavior must still be checked on the target OS.
