# Task 4 Report: Frontend store + event types

## Status: Complete

## Changes

### frontend/src/lib/store.ts
- Added exported types `ToolTrace`, `SourceTrace`, `StepTrace` above `ChatMessage`.
- Extended `ChatMessage` with optional `tools?: ToolTrace[]`, `sources?: SourceTrace[]`, `steps?: StepTrace[]`.
- Extended `ChatStore` interface with `addToolTrace`, `addSourceTrace`, `addStepTrace` action signatures.
- Implemented the three actions in the store, each appending to the last assistant message (mirroring `appendContent`); `addStepTrace` updates an existing step by `id` in place or pushes a new one.

### frontend/src/lib/websocket.ts
- Extended `WSEvent` union with `tool_call`, `source`, and `step` variants, matching the shapes emitted by the backend (Tasks 1-3).

## Verification
- `cd frontend && npx tsc --noEmit` — ran clean, no errors/output.

## Commit
- `b11e255` — "feat(trace): add trace types and store actions" — includes only `frontend/src/lib/store.ts` and `frontend/src/lib/websocket.ts`.

## Concerns
- None. Changes are additive only; no existing behavior modified. Task 5 (rendering the trace strip in chat-interface.tsx / chat-trace.tsx) is not part of this task and remains to be done separately.
