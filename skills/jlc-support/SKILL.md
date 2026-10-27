---
name: jlc-support
description: 'Communicate with JLCPCB (and similar PCB/PCBA manufacturers) online customer service, engineers and sales contacts. Use for status chases on a review or DFM, technical clarifications to the factory about the production file and parts placement confirmation (comparison and interpretation go to jlc-production-review), computing confirmation deadlines, following up after an order is cancelled, quote and coupon requests, asking the factory to take ownership after payment, and refund follow-ups. Check the website and mailbox first, then draft self-contained messages with a boundary statement; sending and any confirmation wait for the user''s consent. Use when drafting or sending messages to JLCPCB support or engineers, chasing a DFM or review, handling a cancelled order, asking the factory about production file changes, or asking for a quote or coupon. Triggers: "JLCPCB support", "JLC support", "chase DFM", "write to JLC", "order cancelled", "production file question", "confirmation deadline".'
---

# JLC Customer Service Communication

There are two goals: every message must get a verifiable answer, and no reply may be treated as you having approved anything.

## Hard rules

Each of the following actions requires the user's explicit consent in the chat every single time; it cannot be inferred from earlier consent:

- Sending an email or a chat message (drafts may be written in advance)
- Downloading the factory's production file or any other file from the website
- Uploading files, accepting terms, submitting an order (including "submit for review without paying")
- Accepting extra fees, compensation or coupon offers
- Confirming the production file (Confirm Production) or the parts placement confirmation (Confirm Parts Placement)
- Modifying the design or manufacturing files

The only exception: the user may, stating the scope and time limit explicitly, pre-authorize two kinds of messages, "status chase" and "pure technical clarification". For example: "until this order ships, status chases with a boundary statement may be sent directly."

- The exception must be written into the project's WORKLOG.
- Every message under the exception must carry a boundary statement; after sending, record the time and content.
- The exception never covers the other actions in the list above: confirmations, fees, compensation, orders, uploads, downloads, design changes.
- If the scope is unclear or the time limit has passed, go back to asking each time.

Payment, national ID numbers and customs clearance details are filled in by the user personally on the web page. The agent does not read, record or relay this content.

Every order-related email is sent from the mailbox the order was registered with, and as a reply in the original thread. If the email tool is connected to a different account, stop first and tell the user.

## Check before writing a message

For tools and fallbacks, see "Tooling" below.

1. Open the order page on the website and look at the **detailed status**, not just the badge at the top of the page. When the top says In Production, the detailed status may still be Data Preparation.
2. Search the registered mailbox, including spam, then read the previous customer-service conversation.
3. Record all IDs (saving the cart may change the number; record both the old and new IDs), the status, the check time and the time zone.
4. When customer service says "the email has been sent" or "it has been handled", check the mailbox before replying. Such claims have been contradicted by another agent from the same company.

## Message structure

Each message contains, in order:

1. Subject: `<requested action> — <order ID>`
2. Greeting
3. One line of background: IDs, the status you just checked, time and time zone
4. One sentence of impact (for example, an upcoming holiday or a deadline counting down)
5. Numbered questions; phrase them as either/or whenever possible
6. Fallback: if no completion time is available, ask for an owner and the next update time (with time zone)
7. Boundary statement, for example: `This is not approval of DFM/production, design changes or extra fees. Please keep manual confirmation.`
8. Thanks and signature

Writing rules:

- **The first message must stand on its own.** Online customer service agents rotate; whoever takes over sees only this one message.
- **Use absolute dates across days.** If you send after midnight, change "today" to "September 28".
- **One email, one topic.** Questions such as refunds or compliance, buried at the end of a long email, went unanswered after being asked three times. Open a separate thread for them; if the email footer has an Escalate Case link, let the user decide whether to use it.
- **Once most questions are answered, follow up only on the remaining point.**
- **Force vague answers into explicit confirmation.** When they say "don't worry" or "just select Yes", ask back with an either/or, for example "all 5 boards, or only 2?"
- **When the website and customer service disagree, paste the website's original text.**
- **Do not accept compensation before the core issue is resolved.** State in the email "I have not yet accepted <compensation> as a resolution."

## Engineering clarification

- State the coordinate system, offset and mm values, for example `original (12.3, 4.5) mm single-board coordinates; CAM offset (+23, +17)`.
- Proactively rule out misunderstandings: say "I am not alleging an open circuit", or "this readout may be the cursor position or the library origin".
- Ask them to attach a marked-up image.
- Do not change the design just to make a displayed value line up; first confirm what that value represents.
- Write important requirements into both the order remarks and an attachment (assembly drawing PDF); the factory CAM side can see the remarks.

## Channels

| Channel | Use |
|---|---|
| Online chat | Real-time Q&A, status chases; before ending, make sure you have a verifiable commitment |
| Registered mailbox | Written evidence, attachments, engineering clarifications; reply in the same thread |
| Sales or partner contact | Only when the usual channels fail or several departments need coordinating. Report progress and explain the impact first, then make the request |
| Order remarks + attachment | Write process requirements in at submission so the CAM side can see them |

## Deadline countdown

When you receive a production file or parts placement confirmation email, immediately compute the absolute deadline (with time zone), write it into WORKLOG and tell the user. Use this skill's script; do not compute it in your head:

```
python -I scripts/deadline.py --received "<time received>" --tz +08:00 --hours 72
```

Exit code 0 means not yet due, 1 means overdue, 2 means invalid input. Copy the "deadline" lines of the output verbatim into WORKLOG. Some confirmation items go straight into production when overdue, so the user must make a decision before the deadline.

Previously observed deadlines are in [references/deadlines.md](references/deadlines.md). That is a snapshot; current emails and the website take precedence.

## Cadence and stop conditions

- When they have not committed to a time, proactive status chases are at least 4 hours apart; monitoring that only checks without chasing can be more frequent. If they give a time, follow that time. This is a lower bound on the interval, not permission to send automatically: every status chase still needs the user's consent, or must fall within the limited exception in the hard rules.
- Notify the user when: there is substantive progress, something fails, a user decision is needed, a deadline is counting down.
- Stop when: they give a final refusal; the report has been obtained and handed to the user; login or the browser breaks (notify once, then pause); the user says pause.
- "We will send an email" or "we are chasing it" does not close the case.

## Tooling

Principle: MCP is only for viewing the current state; scripts compute deadlines and make determinations. An MCP reply of "success" does not mean the message was delivered or the state changed; read back to confirm.

| Step | MCP / tool | Script (relative to this skill folder) | Limits |
|---|---|---|---|
| View detailed order status, customer-service conversation | Browser: Claude in Chrome (Claude Code); ChatGPT browser extension (Codex desktop `@Chrome`; not supported in Codex CLI) | — | Read-only; do not click Confirm or Submit, do not change options, do not download |
| Search registered mailbox, read threads | Mailbox: Gmail connector (claude.ai or ChatGPT) | — | First confirm it is connected to the order's registered account; sending follows the hard rules |
| Draft messages | — | — | Drafts may be written in advance; sending waits for the user's consent |
| Compute confirmation deadline | — | `scripts/deadline.py` | Write the result into WORKLOG |
| Compare production file and parts placement confirmation | — | Hand off to the jlc-production-review skill | This skill only turns its list of open questions into a clarification email |

- The table lists only tools actually used. Other browser or mailbox tools are unverified; before using one, list the actual tool and schema, and do not guess parameters.
- **Fallback without tools**: if there is no browser or mailbox tool (for example in Codex CLI), ask the user to paste the detailed status from the order page, the relevant emails and the previous conversation, then draft. Note in the draft's check record "status provided by the user, not checked directly".

## Include with each delivered draft

Before each draft, show the user these items to help them decide:

1. **Check record**: which sources were checked (order page, mailbox, previous conversation), the check time and time zone; note anything not checked directly.
2. **Message type**: requires per-message consent, or falls within an exception the user pre-authorized (state which authorization).
3. **Suggested channel**: online chat, the original thread in the registered mailbox, or the sales contact, with the reason.
4. **Deadline**: the deadline of the relevant confirmation items (with time zone) and the time remaining.
5. **Draft body**: in English, with a boundary statement.

## Evidence

- For each conversation, save the full chat text as txt and a screenshot of the sent screen, and record the other party's role and the time (with time zone).
- Keep evidence in the project's private directory. Screenshots often contain names, email addresses, phone numbers and addresses; these must be removed before publishing.
- Summaries written by the agent do not count as evidence.

## References

- [references/templates.md](references/templates.md): six templates — status chase, cancellation recovery, technical clarification, quote and coupon, asking for ownership after payment, refund follow-up
- [references/pitfalls.md](references/pitfalls.md): pitfalls hit and lessons learned
- [references/deadlines.md](references/deadlines.md): observed deadlines and customer-service hours (snapshot)
- [references/case-study.md](references/case-study.md): an anonymized timeline of one complete order
- [scripts/deadline.py](scripts/deadline.py): confirmation deadline calculator (standard library only)
