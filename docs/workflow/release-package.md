# Fixed release package

Once manufacturing files are handed over, the fab's questions, customer service exchanges, and extra charges all refer to "the set that was handed over at the time". So the version sent to the fab is made into a fixed release package: its contents no longer change, and progress is recorded elsewhere.

## Keep fixed contents and changing progress separate

| Type | Where it goes | Does it change? |
|---|---|---|
| Fixed release package: native design, libraries, manufacturing files, verification results | `releases/<version>/` or the fixed location agreed for the project | No. To fix something, open a new version |
| Bench test record: power-up and functional test results and errata after boards arrive | Outside the release package, for example `releases/<version>-tests/` | Keeps growing |
| Order, review, and customer service progress | Report files outside the release package, for example `reports/<order>-<date>/` | Keeps being updated |
| Which version to use now | The entry table in the root README | Updated when the baseline changes |

If the README inside a release package mentions a quote or lead time, that is only a snapshot from the release date.

## What a release package contains

```
<board>-<rev>/
├── <board>.kicad_pro / .kicad_sch / .kicad_pcb / .kicad_dru
├── fp-lib-table, sym-lib-table      # ${KIPRJMOD} relative paths
├── footprints/, symbols/            # libraries used by this version, kept as a complete set
├── manufacturing/                   # Gerber + drill zip, BOM, CPL, assembly drawing, schematic PDF
├── verification/                    # ERC, DRC, release-checks.json, review records
└── README.md                        # which files to manufacture from, what was verified, what wasn't
```

- **Libraries use relative paths.** The whole folder still opens when moved to another computer.
- **Do not include** `.kicad_prl` (personal UI state), automatic backups, or manufacturer datasheets.
- Manufacturing files are used **as a set**: Gerber, drill, BOM, CPL, and assembly drawing from the same version.

## Hash list and packaging

[scripts/package_release.py](../../scripts/package_release.py) does four things:

1. Computes SHA-256 for every file in the release package and writes `SHA256-files.json`.
2. Packs the whole folder and the list into a zip.
3. Reopens the zip and compares each file's hash one by one.
4. Writes `.sha256.txt` for the zip itself.

```bash
python scripts/package_release.py --src releases/my-board-revC --out dist
```

The hash list confirms "this is the set from that time"; it cannot be used to restore anything. To be able to restore, keep the complete zip or commit.

`SHA256-files.json` identifies relative paths and file contents; repackaging identical contents should give an identical list. The zip's `.sha256.txt`, however, only identifies **the package file produced this time** and does not guarantee a deterministic rebuild (rebuilding identical contents producing a bit-for-bit identical zip): ZIP keeps metadata such as source file times and permissions, the generated list also carries the time of that run, and the Python/compression library version may affect packaging too. To verify a release package you received, use the ZIP hash that came with it; to compare contents across rebuilds, compare the file lists entry by entry. Don't read a different hash on a rebuilt ZIP as a change in the manufacturing files.

The script's `all_entries_verified: true` only means the content hash check after packaging completed; it does not mean ERC/DRC, CAM/Gerber completeness, fab acceptance, or real-board verification passed.

## release-checks.json

Write the pre-release checks as a machine-readable file so later comparisons and reviews are easy. Suggested fields:

```json
{
  "revision": "C",
  "checked_at": "2026-09-21T18:00:00+08:00",
  "design_file_checks_pass": true,
  "order_readiness": "READY | BLOCKED_<reason>",
  "hardware_validation": "NOT_RUN",
  "blockers": ["unresolved issues that block ordering, described by role, not by name"],
  "checks": [
    { "check": "ERC no violations or ignored checks", "pass": true, "detail": null },
    { "check": "DRC: no violations, unconnected items, parity issues", "pass": true, "detail": null },
    { "check": "R5: schematic MPN, C-code, footprint and BOM agree", "pass": true, "detail": null },
    { "check": "Gerber zip contains In1_Cu", "pass": true, "detail": null }
  ]
}
```

- `hardware_validation` is always `NOT_RUN` until the real board has been tested.
- Things that change, such as stock and attrition, go in `detail` with a date and are not counted as passing.

## Naming version folders

The process often leaves several similar copies behind. Names should make their purpose clear:

| Name | Meaning |
|---|---|
| `before-complete.zip` | Complete backup before the change |
| `candidate/` | Candidate version being modified |
| `review-snapshot.zip`, `review-r1-fixed.zip` | Fixed version handed over for review, and the version after first-round fixes |
| `<board>-<rev>-<YYYYMMDD>.zip` | Official release package |

`candidate`, `review`, and `fixtures` also contain PCBs with the same name, but they are not the current fixed release package, and they must not be deleted just because the file names repeat. Which version to use now is set by the README entry table.
