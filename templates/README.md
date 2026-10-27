# <Project name> | Project entry

<!-- This page covers only "now": which version to look at and what's left. History goes in the WORKLOG. -->

Updated: <YYYY-MM-DD>. <One or two sentences on what this project does, which development lines exist, and overall progress. If something hasn't been bench tested, say so.>

## Usually all you need

| What you want to do | Where to go | Current status |
|---|---|---|
| See the board currently being manufactured | [<version> release package](<path>/README.md) | <size, layer count, assembly method> |
| Check ordering / review progress | [<order report>](<path>) | <latest status and date; where it stopped, who it's waiting on> |
| Continue <other subproject> | [<entry doc>](<path>) | <status> |
| Use KiCad automation tools | [Tool workflow](<path>) | <how far verified> |

## Don't mix versions

| Version / location | Purpose | How to treat it now |
|---|---|---|
| `<releases/board-revC/>` | <description> | **Current manufacturing baseline** |
| `<board-revB/>` | <description> | Old design kept for reference, not the current manufacturing version |
| `<reports/.../candidate/>` | Candidate version from the modification process | Intermediate copy, not the current release package |

## Remaining work

1. **<Subproject>:** <what isn't done yet, and where it's stuck>
2. **<Subproject>:** <…>

This is a to-do index; it does not automatically resume other work, place orders, or operate the GUI.

## Where other material lives

- [WORKLOG.md](WORKLOG.md): trace decisions and handoffs chronologically; normally read this page first.
- [AGENTS.md](AGENTS.md): collaboration and design change rules.
