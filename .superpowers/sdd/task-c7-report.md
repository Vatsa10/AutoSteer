# Task 7: Outcomes gallery — launch flagship workflows

## Status: Done

## Commit
`04962d043f47f17480cfab3c41d05414305505dd` — "feat(outcomes): gallery cards launch flagship workflows"

Files committed:
- `frontend/src/app/(main)/templates/page.tsx`
- `frontend/src/components/chat-interface.tsx`

## Changes

### 1. `frontend/src/components/chat-interface.tsx`
- Extended the template-prompt effect (~line 69-79). Non-`run `-prefixed prompts keep prefill-only behavior (`setInput`). Prompts matching `/^run\s+\S/i` now also auto-send: after `setInput(templatePrompt)`, a `setTimeout(..., 60)` dispatches a `MouseEvent("click", { bubbles: true })` on `document.getElementById("chat-send-btn")`, giving React time to flush `setInput` so the submit button (disabled when input is empty) is enabled before the synthetic click fires.
- Added `id="chat-send-btn"` to the existing `<button type="submit">` inside `<form onSubmit={handleSubmit}>` (was already a real submit button at ~line 428 pre-edit; no need for the fallback `submitText` refactor described in the plan).

### 2. `frontend/src/app/(main)/templates/page.tsx`
- Added imports: `useEffect`, `useState`, `Play` icon, `getWorkflows`/`WorkflowDefinition` from `@/lib/api`.
- Added `FLAGSHIP` static list (research_report, content_approval, contract_redline) with title/outcome/chips per plan.
- Reused existing `router` and `setConversationId` (not redeclared).
- Added `available` state populated via `getWorkflows()` on mount (best-effort, swallows errors) to gray out cards for workflows not present on the backend.
- Added `runOutcome(name)` that sets `sessionStorage["autosteer_template_prompt"] = "run <name>"` and routes to `/chat`.
- Rendered the Outcomes section (3-card grid, slate/blue theme: `bg-white`, `border-slate-200`, `rounded-xl`, blue accent button) above the existing template-category sections, matching the plan's JSX exactly.

## Verification
- `cd frontend && npm run build` — clean build, no TypeScript errors, `/templates` route present in the route list (static). Full route table confirms `○ /templates`.
- Step 4 (live-browser E2E: click "Run outcome", confirm auto-send + workflow stream + approval flow) was **skipped** — no dev/backend servers were started in this session per task instructions permitting skip when servers can't run. This is a residual manual-verification gap; the auto-send wiring (id + click dispatch + regex gating) was verified by code inspection only, not by driving the browser.

## Concerns
- Auto-send correctness (timeout race, button-disabled timing) is unverified at runtime — recommend a manual smoke test of `/templates` → "Run outcome" → chat auto-submits before shipping.
- `getWorkflows()` availability check silently no-ops on fetch failure (`.catch(() => {})`), so if the backend is down all three cards render enabled (since `available.size === 0` short-circuits the disabled check) — matches plan behavior but means "disabled" state only activates once the workflow list successfully loads and a given name is absent from it.
