# Fix C7 Report

## Status
DONE

## Commit
33e7b5a

## Build
`npm run build` in frontend/ — clean, no type errors, no lint failures.

## Summary
Extracted `handleSubmit`'s body into a `submitText(rawText, attach=[])` useCallback
(declared after `sendViaWebSocket`, before `handleSubmit`/deep-link effect). The
template-prompt effect's "Run" branch now calls `submitText(templatePrompt, [])`
directly instead of `setInput` + `setTimeout(60)` + synthetic click on
`#chat-send-btn`. `handleSubmit` now just calls `submitText(input, attachments)`,
preserving normal typed-message behavior. Removed the now-unused
`id="chat-send-btn"` attribute from the submit button.

## Concerns
None. Behavior for the normal typed-submit path is unchanged; only the
outcome-launch auto-send path was hardened.
