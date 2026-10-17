# Activity form: keep a draft on the device

Long activity write-ups can be lost if a phone kills the browser tab before Save. The idea is to keep the unsaved form in `localStorage` per activity and offer to restore it the next time the form opens. This is a per-device convenience only; the database stays the source of truth.

Raised during planning, 2026-10-16. Not in v1.
