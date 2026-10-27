# Factory Production File and Parts Placement Review

After payment, contract manufacturers such as JLCPCB ask you to confirm two things: the PCB production file and the PCBA parts placement. This page explains how to diff the factory-modified files item by item against the version you submitted, decide which changes are normal and which need questions, and which actions must wait for the user to decide.

Rules and templates for communicating with the factory are in the [jlc-support skill](../../jlc-support/SKILL.md). The diff scripts are described in [cam-diff.md](cam-diff.md); the scripts themselves are in this skill's `scripts/`.

## When to use

| Confirmation item | Content | Observed deadline |
|---|---|---|
| PCB production file (Production file / Confirm Production) | Gerbers after factory CAM processing: copper, holes, solder mask, silkscreen, outline, often placed in a process frame with added rails | The email asks for confirmation within 48 hours "to avoid delay"; it does not say production starts automatically when overdue |
| PCBA parts placement confirmation (Confirm Parts Placement) | Part number, position, rotation and polarity of every component | The email says production starts directly if not confirmed within 72 hours |

- Review and confirm the two separately. A correct bare board does not mean the component orientations are correct.
- **Compute the absolute deadline the moment the email arrives**: received time plus the deadline period, with the time zone stated. For example, a 72-hour notice received Monday 16:02 (UTC+8) expires Thursday 16:02 (UTC+8). Write it into WORKLOG and tell the user right away.
- The deadline in the current email and on the website governs; past observations are in [deadlines.md](../../jlc-support/references/deadlines.md).
- Options on the website confirmation page may appear selected as soon as it opens. That does not mean they have been submitted. Do not change them, and do not click Submit.

## Preparation

1. **Lock the comparison baseline.** Use the fixed release package you actually submitted (Gerbers, drill, CPL, BOM, assembly drawing). Do not compare against a newer design or a historical version.
2. **Obtain the factory files.** Downloading requires the user's consent, or the user downloads them and provides the path. Keep the original ZIP, record its SHA-256, and store it in a private directory.
3. **Understand the ZIP structure.** JLCPCB example: `YG` is a copy of your original submission, `ok` is the CAM file after engineering processing ([official explanation](https://jlcpcb.com/help/article/how-to-confirm-the-production-file)). Sometimes ODB++ (`.tgz`) is included too. What you review is `ok`; do not rely on the small preview on the website.
4. **First confirm the factory received the right version.** Compare the SHA-256 of every member file of the original submission copy against the fixed package (`render_compare.py --check-upload`). Compare the extracted members, not the ZIP itself.

## Layer mapping

These are the file names of one JLCPCB production file; other factories or other orders may differ.

| File name | Meaning | What to look at |
|---|---|---|
| `tl` / `bl` | Top/bottom copper | Whether pads or traces disappeared, moved or touch each other |
| `l2` / `l3` (plus `l4` `l5` for 6 layers) | Inner copper layers | Planes, clearance gaps, pad treatment around holes |
| `ts` / `bs` | Top/bottom solder mask | The graphics are "openings that expose copper", not the green mask itself |
| `to` / `bo` | Top/bottom silkscreen | Designators, pin 1, polarity and header markings |
| `drl` | Drill | Count, position, diameter; although named drl, this file is Gerber, not Excellon |
| `ko` | Outline | Finished board outline and process frame; not every line is a cutter path |
| `vcut` | V-cut engineering drawing | Only lines marked V-CUT are cut lines; dimension lines and the outer frame are not |
| `sk` | Hole treatment markings | Not another drill list; the treatment is per the engineering notes |

Files often have no extension, and units are often inches (e.g. 2.6 format). When opening them in KiCad's Gerber Viewer, switch the file filter to show all files if the extension is blank.

## Steps

### 1. Find the coordinate transform

Factory files usually use process frame coordinates: the single board is translated, sometimes rotated, with rails, tooling holes and fiducials added around it.

- First measure the single board size and the process frame size. The large frame is for processing, not the finished size.
- Find the offset: drill holes are the most accurate; `render_compare.py --offset auto` estimates it from hole positions. You can also find the corners of the single board outline in `ko`. Example: original single-board coordinates plus (+23, +17) mm, no rotation or mirroring.
- When a panel has several identical single boards, compare each position once. A drawing that shows only one processing unit cannot prove the delivered quantity or that every board will have its rails removed.
- Every coordinate recorded afterwards states its frame: "original single board (x, y) mm, offset (+dx, +dy)".

### 2. Compare layer by layer

Use a new private output directory every time; after running, check the exit code and JSON `status`. WARNINGs must be classified and followed up; INCOMPLETE/ERROR must have the missing data supplied or be fixed and rerun. Do not write PASS because some layers succeeded, there are no difference boxes, or a report was generated. A `render_compare` PASS only covers input and rendering; it does not replace the later diffs or the user's approval. The status contract, how to record an excluded missing paste layer, and relative-path pairing are in [cam-diff.md](cam-diff.md#results-and-stop-conditions).

```
python scripts/render_compare.py --original <fixed package gerbers.zip> --factory <factory production file> --offset auto --out <private directory>
python scripts/pixel_compare.py --renders <private directory>
python scripts/check_inner_removals.py --renders <private directory>
```

Then visually recheck in a Gerber viewer: first open only `ko` and `drl`, then open copper, solder mask and silkscreen one layer at a time; do not stack everything at once. Switching to a bottom view flips left and right, so always describe differences in top-view coordinates to avoid misreading a mirror.

Questions to answer for each layer:

- **Copper**: Are all original pads, traces and copper pours still there? Has anything moved?
- **Solder mask**: Has any original opening been covered? Enlarged openings and added openings at the board edge are routine processing.
- **Paste**: Production files often do not include the paste layer. When the factory provides a separate stencil file, compare it too with `--pair`.
- **Silkscreen**: Are designators, pin 1 and polarity markings still there? Trimming to avoid pads is routine processing.
- **Drill**: Is the hole count the same? Has any hole moved? Finished hole size and drilled hole size may differ (for example, a 1.0 mm finished plated hole drilled at 1.15 mm); check which one the factory is labeling. Are all added holes outside the finished board?
- **Outline**: Is the finished size correct? Which lines are actually V-cut? Are components near cuts or milled edges safe?

### 3. Classify every difference

| Routine CAM processing (still record it) | Suspicious, ask about it or request a fix |
|---|---|
| Rails, tooling holes outside the finished board, fiducials, panel V-cut or mouse bites | Original pads, traces or copper pour disappeared |
| Copper pour on the rails | Copper of different nets touching |
| Copper compensation (trace width and pads slightly enlarged) | Pads or components moved; a hole offset from its own pad |
| Teardrops | An original hole missing, or an extra hole inside the finished board |
| Unused isolated pads (non-functional pads) removed on inner layers | A hole on a plane net (such as GND) losing its inner-layer connection |
| Enlarged solder mask openings, board-edge openings | Solder mask covering an original opening |
| Silkscreen trimmed to avoid pads | Designator, pin 1 or polarity marking deleted |
| Via moved slightly with matching rerouting (e.g. moved 0.06 mm to avoid overlapping a pad's solder mask opening) | Finished size or outline changed; depanelization method endangering edge components |
| Drill enlarged for hole wall compensation | Any change without an explanation |

"Routine" does not mean "no problem this time". For changes like a slightly moved via, even if they look reasonable, record the position and magnitude, ask the factory to explain why, and confirm their netlist comparison result.

### 4. Where copper changed, check connectivity

- **Moved holes**: the hole and its pad on every layer must move together, and the top and bottom layers must have new connecting traces that join it back to the original trace. Only the hole moving without the pad, or a missing connecting trace, indicates an open circuit. Also check clearance to adjacent copper after the move.
- **Inner-layer copper removal**: use `check_inner_removals.py` to confirm only unconnected isolated pads were removed. Export a hole list with net names from KiCad (see [cam-diff.md](cam-diff.md#generating-holesjson-with-net-names-from-kicad)), add `--plane-nets GND`, and confirm holes on plane nets keep their connections.
- **A raster diff is not a netlist proof.** The resolution is about 0.025 mm/pixel, suited to finding differences, not to proving manufacturing tolerances. Ask the factory for their netlist comparison result between the original files and the CAM file; electrical testing is a separate matter.

### 5. Check PCBA placement

On the parts placement confirmation page, choose Top (or Bottom) and 2D, and turn on Show Components and Show Designator. Clicking a designator in the table zooms to that component. 3D is good for recognizing positions; for polarity, the 2D markings govern, checked against the assembly drawing.

- **Count and part numbers**: placement count and part number types match the BOM; do-not-place (DNP) parts do not appear in the placement list.
- **Position**: the expected position is the CPL single-board coordinate plus the common offset. If the assembly data contains coordinates carried over from an old panel, do not use them directly; recompute from single-board coordinates.
- **Rotation and pin 1**: check against the silkscreen, the assembly drawing and the datasheet pinout. For diodes look at K/A; bidirectional ESD parts have no polarity and cannot be judged by rectifier diode rules; check MOSFETs against G/S/D; for modules look at the pin 1 marking.
- **Engineering change markers**: turn on an option such as Show Revised Items and confirm one by one what was changed on each modified component.
- **A blank DFM result column** does not mean the factory did a full check.
- **The website reading is not necessarily the placement center.** The X/Y shown after selecting a component may be the cursor, the library origin or the pick point. Some connectors have a mechanical center that differs from the signal pad center by design. When the reading differs from the CPL (e.g. by 0.9 mm), do not call it a component offset, and do not ask to move the component just to make the numbers match; first ask the engineer what that number represents, and mark the actual solder joints on the drawing.

## Writing clarifications to the factory

Use [template C (production file technical clarification) in templates.md](../../jlc-support/references/templates.md); it is not repeated here. Key points:

- State the coordinate frame: original single-board coordinates (x, y) mm, offset (+dx, +dy) mm, and the coordinates seen in the factory file.
- Say up front "this is not a claim of a defect"; only ask for the reason for the change and the check result (e.g. whether the netlist comparison passed).
- Ask them to attach an annotated drawing.
- Do not ask to move components to make the displayed values line up.
- Put all open items in one message; once they have answered most of them, follow up only on what remains.
- Be specific about requests involving quantity or scope, e.g. "remove the rails from all N boards".
- End with a boundary statement: this is a technical inquiry, not an approval; please keep manual confirmation.

## Who may do what

| Action | Who decides |
|---|---|
| Compute the deadline, write it into WORKLOG, remind the user | Agent handles on its own |
| Read emails and website status (without changing any option) | Agent handles on its own |
| Run diff scripts, make difference images, classify, write the review report | Agent handles on its own |
| Draft clarification messages | Agent handles on its own |
| Download factory files | User consents, or the user downloads them |
| Send an email or chat message | User's explicit consent in chat every time; status chases and pure technical clarifications may be pre-authorized under the limited exception in jlc-support's hard rules |
| Click Confirm Production, Confirm Parts Placement, Submit, or change confirmation options on the website | User's explicit consent in chat every time |
| Accept factory changes, extra charges, compensation or rescheduling | User's explicit consent |
| Ask the factory to move components or modify CAM | User's explicit consent |
| Modify the design or the fixed release package | User's explicit consent, and open a new version |

When the deadline is approaching and the user has not decided, remind once more; do not confirm on their behalf. Neither not replying nor not clicking confirm guarantees the factory will not start production automatically after the deadline.

## Records

- Record in WORKLOG: received time and deadline, comparison baseline and its hash, coordinate transform, the classification of every difference, questions sent, and open items.
- Screenshots and emails often contain names, email addresses and addresses; keep them in a private directory and scrub them before publishing.
- How to word the conclusion: "No clear wrong version, missing holes or polarity errors found; the following N items await factory explanation". Whether to go into production is the user's decision; the agent never writes "ready for production".

## Limitations

- This diff looks at graphical differences; it does not redo ERC/DRC, nor is it an electrical, RF or EMC assessment.
- The factory's depanelization order, tool compensation, hole treatment process and actual placement centers cannot be proven from drawings alone; they need written engineering replies.
- The review can only speak to the files; it cannot verify boards not yet made.

## References

- [JLCPCB: How to confirm the production file](https://jlcpcb.com/help/article/how-to-confirm-the-production-file)
- [JLC (Jialichuang): notes on removing isolated inner-layer pads](https://www.jlc.com/portal/server_guide_39501.html) (explains the purpose of removing non-functional pads on inner layers)
