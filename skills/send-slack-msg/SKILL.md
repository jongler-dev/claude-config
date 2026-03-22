---
name: send-slack-msg
description: Send Slack messages to users by name with automatic user ID caching. Use when the user asks to send a Slack message, DM, or ping someone on Slack. Triggers on phrases like "send a message to", "DM", "slack message", "tell [name] on slack", "ping [name]". Handles user lookup, caching, and message delivery via Slack MCP tools.
---

# Send Slack Message

Send Slack messages to users by display name with a persistent user ID cache to avoid repeated lookups.

## Cache

- **Location**: `~/.claude/cache/slack-users.json`
- **Format**: `{ "lowercase display name": { "user_id": "U...", "email": "...", "title": "..." } }`
- Read the cache file at the start. If it doesn't exist, treat as empty `{}`.

## Workflow

1. **Read cache** from `~/.claude/cache/slack-users.json` (create parent dir if needed)
2. **Resolve user ID**:
   - Normalize the target name to lowercase
   - If found in cache, use the cached `user_id`
   - Otherwise, call `slack_search_users` with the name, pick the best match, and proceed
3. **Send message** via `slack_send_message` with `channel_id` set to the user's `user_id`. If the send fails and the user ID came from cache, retry by doing a fresh `slack_search_users` lookup and updating the cache before reporting failure.
4. **Update cache** on successful send:
   - Add/update the entry keyed by lowercase display name
   - Write the updated JSON back to the cache file
5. **Return** the message link to the user

## Notes

- If `slack_search_users` returns no results, tell the user no match was found and ask them to verify the name.
- When the user provides a partial or ambiguous name and multiple results come back, ask which user they mean before sending.
- The cache is append-only; entries are never removed automatically.
- To clear a stale entry, the user can ask to "clear slack cache for [name]" or "reset slack cache".
