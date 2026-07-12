# Task 5: Artifact card in chat + sidebar link — Report

## Status
Complete (Steps 1-5, 7 done; Step 6 live E2E skipped — see Concerns).

## Commit
f7818fbde1b567f444cc48a1443c347c731c5276
"feat(artifacts): artifact card in chat + sidebar link"

Files committed:
- frontend/src/lib/store.ts
- frontend/src/lib/websocket.ts
- frontend/src/components/chat-interface.tsx
- frontend/src/components/sidebar.tsx

## Changes

### frontend/src/lib/store.ts
- Added `ArtifactRef` interface: `{ id, title, kind, filename: string | null }`.
- Added `artifacts?: ArtifactRef[]` to `ChatMessage`.
- Added `addArtifactRef: (a: ArtifactRef) => void` to `ChatStore` interface and implemented it, mirroring `addToolTrace`/`addSourceTrace` (appends to the last assistant message's `artifacts` array).

### frontend/src/lib/websocket.ts
- Extended the `WSEvent` union with `{ type: "artifact"; id: string; title: string; kind: string; filename: string | null }`.

### frontend/src/components/chat-interface.tsx
- Added `const addArtifactRef = useChatStore((s) => s.addArtifactRef);` alongside the other trace hooks (`addToolTrace`, `addSourceTrace`, `addStepTrace`).
- Added a `case "artifact":` branch in the WS `onEvent` switch, calling `addArtifactRef({ id, title, kind, filename })`.
- Added an artifact card block directly after the existing `<ChatTrace .../>` render (inside the assistant bubble), rendered only when `msg.artifacts.length > 0`. Each artifact renders as a link to `/artifacts` with a kind badge, title, and "View →" affordance, styled with the existing slate/blue theme (`border-slate-200`, `bg-white hover:bg-slate-50`, blue badge/accent) to match Plan A's `ChatTrace` and the rest of the inner app.

### frontend/src/components/sidebar.tsx
- Imported `FileText` from `lucide-react`.
- Added `{ href: "/artifacts", label: "Artifacts", icon: FileText }` to the `navItems` array, positioned between "Approvals" and "History". This single array is consumed by both the collapsed-icon-rail rendering and the expanded nav list, so no other markup changes were needed — the new entry automatically gets identical `<Link>` styling/active-state handling as existing items.

## Build Summary
`cd frontend && npm run build` — compiled successfully in ~1.4s, TypeScript check passed, all pages (including `/artifacts`, statically prerendered) generated with no errors or warnings related to these changes.

## Concerns
- Step 6 (live E2E: ask agent to "create a docx report", confirm artifact card appears, `/artifacts` lists it, approve flips badge) was **not run** — dev servers (backend + `npm run dev`) were not started in this session per task instructions allowing this to be skipped when servers can't run. The build-level verification (Step 5) passed cleanly, and the code changes are a straightforward, structurally-verified mirror of the existing Plan A trace-event pattern (tool_call/source/step → addToolTrace/addSourceTrace/addStepTrace), so runtime behavior should match, but this has not been observed in a live browser.
- No existing frontend tests reference `store.ts`/`websocket.ts`/`chat-interface.tsx`/`sidebar.tsx` artifact behavior, so no automated regression coverage was added or run beyond `npm run build`'s type-checking.
