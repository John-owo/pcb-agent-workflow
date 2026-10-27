# Collaboration and handoff

Applies when one person works with one or more agents (Claude Code, Codex) on the same board, with the work spanning several days and changing hands several times.

## One writer per working directory

- A working directory and a KiCad GUI have only one writer (person or agent) at a time.
- At handoff, the side handing over stops writing first and records the stopping point; the side taking over checks it before starting to write.
- For parallel development, open separate git worktrees and write down clearly what each one is responsible for.
- External hardware (dev boards, serial ports, measurement instruments) is likewise operated by a single owner.

For the handoff format between Codex and Claude Code, see [codex-cc-handoff](https://github.com/John-owo/codex-cc-handoff).

## Entry documents and WORKLOG

Each project has two entry points:

- **README.md**: the current state. Which version to look at now, what is still unfinished, where each kind of material lives. Update it whenever the design baseline or the resume point changes.
- **WORKLOG.md**: a chronological work log, newest at the top. Each entry records the owner, scope, what was changed, how it was verified, where it stopped, and the next step.

See the templates [templates/README.md](../../templates/README.md) and [templates/WORKLOG.md](../../templates/WORKLOG.md).

How to read the WORKLOG:

- Later corrections override earlier statements.
- A "next step" in the history was only the plan at the time and does not grant new authorization to act. What to do after taking over is set by the user's current request.
- Things whose status changes (orders, reviews) go in a dedicated report file; the WORKLOG only gets a one-line summary and a link.

## Takeover order

1. Read the README and pick the sub-project and version based on the user's current task.
2. Read the top of the WORKLOG and the latest entries relevant to this task; check the owner, the stopping point, and anything still waiting for the user's confirmation.
3. Check the actual target files and uncommitted git changes. Start writing only once you can clearly state the sub-project, file paths, version, and scope of work. If you can't map it to a sub-project, ask first.

## Before changing a design

- **First secure a recoverable version.** Make a complete copy of the design and the libraries it depends on, or create a checked commit. A hash list only identifies files; it cannot be used to restore them.
- **After changing, check:** netlist, ERC, DRC, and the diff against the version before the change.
- **Don't run the initial board-generation script on a finished board.** Such scripts rebuild the whole board and wipe the routing.

## Actions that require the user's explicit consent

Each of the following requires the user's consent in the conversation every time; consent cannot be inferred from earlier consent:

- Paying, submitting an order, submitting for review
- Sending emails or customer service messages
- Confirming the production file or parts placement
- Pushing, publishing, any irreversible operation
- Accepting extra charges, compensation, or design changes

The agent can do the analysis, write drafts, and prepare upload files first, stopping before any button is pressed.

The only exception is status chases and pure technical clarifications: the user can authorize these two kinds of messages in advance by explicitly stating the scope and time limit. For details see [jlc-support's hard rules](../../skills/jlc-support/SKILL.md).

## Review

- For complete features, cross-module changes, significant PCB changes, and delivery milestones, have another agent review a **fixed version** (snapshot or commit).
- Two rounds at most. The reviewer presents evidence; the owner judges and makes changes. Don't let two agents review each other endlessly.
- The reviewer gets only file-reading and search tools; MCP writes, unreviewed hooks, and shell are disabled. Don't use options that skip permissions.
- If a review fails, runs out of quota, or produces a blank or partial report, mark it "review incomplete"; don't treat it as passed.

## Rules for drawing conclusions

- Passing ERC/DRC does not mean electrically correct, accepted by the fab, or that the real board works.
- Conclusions about pinouts, RF, power, and component values must be checked against the manufacturer's datasheet or reference design.
- A summary written by an agent is not evidence. Evidence is the original files, command output, and verbatim records.
- State explicitly what was not done, for example "SPICE timed out, marked SKIP, does not count as PASS".
