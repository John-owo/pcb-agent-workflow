---
name: jlc-production-review
description: 'Review the PCB production file (Confirm Production) and PCBA parts placement confirmation (Confirm Parts Placement) that JLCPCB sends after payment: align the factory CAM-modified Gerbers back to the fixed release package you submitted, diff copper, holes, solder mask, silkscreen and outline layer by layer, check placement count, position, rotation and polarity, classify every difference, and write a list of questions for the factory; confirming and sending messages wait for the user to decide. Includes diff scripts and a BOM/CPL check. Use when reviewing a JLCPCB production file or parts placement confirmation, diffing factory CAM Gerbers against the original release, or checking BOM/CPL before upload. Triggers: "review production file", "diff production file", "parts placement confirmation", "factory changed the Gerbers", "BOM CPL check", "confirm parts placement", "CAM diff".'
---

# JLC Production File and Parts Placement Review

Goal: before the deadline, give the user a review result they can base a decision on. The agent only diffs, classifies and drafts; confirming, sending messages and downloading all wait for the user.

## Hard rules

Each of the following actions requires the user's explicit consent in chat, every time:

- Downloading factory files from the website (or asking the user to download them and give you the path)
- Clicking Confirm Production, Confirm Parts Placement, Submit, or changing confirmation options on the website
- Accepting factory changes, extra charges, compensation or rescheduling; asking the factory to move components or modify CAM
- Modifying the design or the fixed release package

Options on the confirmation page may appear selected as soon as it opens. That does not mean they have been submitted; do not touch them. The conclusion only says "No clear wrong version, missing holes or polarity errors found; the following N items await factory explanation". Never write "ready for production".

Communication with the factory (sending clarification messages, status chases) is handed to the jlc-support skill. If it is not installed, draft per the "Writing clarifications to the factory" section of this skill's [references/procedure.md](references/procedure.md); sending still waits for the user's consent.

## Workflow

1. **Compute the deadline.** On receiving the email, add the deadline to the received time, convert it to an absolute time with time zone, write it into WORKLOG and tell the user. An overdue PCBA parts placement confirmation goes straight into production. If jlc-support is installed, use its `scripts/deadline.py`.
2. **Lock the baseline.** Use the fixed release package actually submitted, not a newer design. Store the factory ZIP in a private directory and record its SHA-256.
3. **Confirm the factory received the right version.** Run `render_compare.py --check-upload` to compare the original submitted copy (JLC's `YG`) with the fixed package.
4. **Diff layer by layer.** Run the three scripts on the factory CAM file (`ok`), each time with a new private output directory, then visually recheck in a Gerber viewer.
5. **Classify differences.** Record routine CAM processing as is; list suspicious items as questions. The classification table is in section 3 of procedure.md.
6. **Check placement.** Count, part number, position (CPL single-board coordinates plus a common offset), rotation, pin 1 and polarity.
7. **Deliver.** Review report, question list, clarification message draft and remaining time to the deadline, handed to the user to decide.

## Tooling

Principle: MCP looks at the current state; scripts make the call. An MCP reply of "success" does not count as acceptance.

| Step | MCP / tool | Script (relative to this skill folder) | Pass condition |
|---|---|---|---|
| View confirmation page and deadline info | Browser: Claude in Chrome (Claude Code); ChatGPT browser extension (Codex desktop `@Chrome`; Codex CLI not supported). Read-only: do not click options, do not download | — | Detailed status and check time recorded |
| Find the confirmation email | Mailbox: Gmail connector (claude.ai or ChatGPT). First confirm it is connected to the account the order is registered under | — | Received time and deadline recorded |
| Version check, alignment, drill diff | — | `scripts/render_compare.py` | Check exit code and JSON `status` |
| Per-layer pixel diff | — | `scripts/pixel_compare.py` | Every WARNING classified |
| Inner-layer copper removal | — | `scripts/check_inner_removals.py` (can take `holes.json`) | Only isolated pads removed |
| BOM/CPL before and after placement | — | `scripts/check_bom_cpl.py` | PASS, or every WARNING has a reason |

- Install dependencies: `python -m pip install -r scripts/requirements-cam.txt` (Python 3.12). `check_bom_cpl.py` uses only the standard library.
- Exit code 0 is PASS, 1 is WARNING, 2 is INCOMPLETE or ERROR. INCOMPLETE/ERROR must never be written up as a pass; having a report, having images, or having no orange boxes also does not mean PASS.
- Without browser or mailbox tools, ask the user to paste the confirmation email content and page status, and note in the report "Status provided by the user, not checked directly".
- The scripts only look at graphics and do not understand nets; a raster diff is not a netlist proof. Ask the factory for its netlist comparison result.

## Stop conditions

- Script INCOMPLETE/ERROR: supply the missing data or fix and rerun; do not hand in results from a partial set of layers.
- Deadline approaching and the user has not decided: remind once more; do not confirm on their behalf.
- Suspicious difference found: stop at drafting the clarification message and wait for the user to decide whether to send it.

## References

- [references/procedure.md](references/procedure.md): full review procedure: layer mapping, coordinate transform, difference classification table, placement check, who may do what, record keeping
- [references/cam-diff.md](references/cam-diff.md): options, result states and limitations of the three diff scripts, and how to produce `holes.json`
