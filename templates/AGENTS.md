# <Project name>: agent collaboration rules

<!-- Copy to the project root. Replace <...> with your own content and delete sections you don't need. See docs/workflow/ in pcb-agent-workflow for the workflow. -->

## Taking over

1. First read the root [README.md](README.md) and, based on the user's current task, pick the subproject and current version.
2. Read the top of [WORKLOG.md](WORKLOG.md) and the latest entries relevant to this task; check the stopping point, owner, and items still awaiting the user's confirmation. A "next step" in past entries does not grant new authorization to act.
3. Before modifying, check the actual target files and uncommitted git changes. Start writing only once you can clearly state the subproject, design path, version, and scope of work. If the task maps to no subproject, ask first.

Read by task:

- **<Subproject A, e.g. GNSS test board>**: enter from "Current manufacturing baseline" in the README. <List easily confused version folders and say which one is current>
- **<Ordering / customer service>**: enter from the order progress entry in the README; quotes inside a release package are only a snapshot from the release date.
- **<Firmware>**: read <subproject README path>.
- **KiCad tools**: read <tool workflow doc path>.

When the design baseline or the takeover entry changes, update the README too; record changes, verification, and stopping points in the WORKLOG.

## Collaboration rules

- One working directory, one KiCad GUI, one writer at a time. When handing off, record owner, version, changes, tests, and next step in the WORKLOG. For parallel development, use separate worktrees and state the scope clearly.
- Before review, secure the complete design and dependent libraries (a snapshot or a checked commit). A hash manifest only identifies files; it does not replace a backup. A plain worktree does not include uncommitted changes.
- For complete features, cross-module changes, significant PCB changes, and delivery milestones, have another agent review a fixed version, at most two rounds. The reviewer provides evidence; the owner decides and makes changes. Mark failed, out-of-quota, empty, or partial reports as incomplete reviews.
- Automated reviewers get only file-reading and search tools; MCP writes, unreviewed hooks, and shell are disabled. Do not use permission-skipping options, and do not let agents call each other indefinitely.

## Design rules

- Use the native KiCad CLI for ERC, DRC, exports, and manufacturing files. Check the installed version's `--help` first.
- Before modifying the PCB, secure a recoverable version; after modifying, check the netlist, ERC/DRC, and diffs. The GUI, the board, and external hardware are each controlled by one owner only.
- The initial board-creation script for <the routed production board> rebuilds the whole board and must not be run on the finished production board.
- Conclusions about pinout, RF, power, and component values must be checked against vendor documentation. Passing ERC/DRC does not mean electrically correct, accepted by the fab, or passing real-board testing.
- When saving backups and files, keep project-relative library paths (`${KIPRJMOD}`).
- Payment, order submission, sending email, confirming production files, publishing, pushing, and other irreversible actions each require the user's explicit consent every time; consent cannot be inferred from earlier consent.
- The only limited exception for customer service messages: the user may explicitly specify a scope and deadline to pre-authorize "status chase" or "pure technical clarification" messages. Record the authorization in the WORKLOG per the `jlc-support` hard rules; every message carries the boundary statement, and after sending, record the time and full text. If the scope is unclear or the deadline has passed, confirm each time. This exception does not cover confirming production files / parts placement confirmation, fees, compensation, orders, uploads, downloads, or design changes, and does not authorize publishing or pushing.
