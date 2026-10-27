# KiCad tools: native CLI and Konnect MCP

Describes the division of labor between tools when an agent (Claude Code, Codex) works on a KiCad 10 design, version pinning, the Konnect call order, `kicad-cli` commands, and checks before and after changing a PCB. The content is compiled from a project that has been sent to JLCPCB for manufacturing; versions and observations are dated, so recheck against the version you installed before use.

## 1. Division of labor

| Task | Tool | Notes |
|---|---|---|
| ERC, DRC, schematic parity | `kicad-cli` | Native CLI results are authoritative |
| Gerber, drill, BOM, CPL, PDF | `kicad-cli` or the project's own export scripts | MCP exports are only auxiliary, not manufacturing deliverables |
| Reading project, schematic, board info | Konnect | Check the `source` field when reading back |
| Schematic editing | Konnect `sch_*` toolsets | After saving, check with native netlist, ERC, and file diff |
| Live PCB editing | Konnect, via KiCad IPC | The GUI must have the exact target open with the API enabled (section 3) |
| Updating schematic to PCB | KiCad GUI "Update PCB from Schematic" | Konnect's sync feature is not yet verified |
| Auto-placement, autorouting | No verified equivalent | See the capability table in section 3 and section 8 |
| Electrical analysis (EMC, SPICE, datasheet) | Analysis skills + native CLI | Doesn't depend on MCP |
| Backup | Complete project copy, or a checked commit | `snapshot_project` only produces a PDF; it is not a backup |

- **Single writer.** A design has only one writer at a time: one agent, one MCP server, or the user operating the GUI. While the user is operating the KiCad window, the agent stops UI input and waits for the user's explicit notice before continuing.
- **stdio fallback.** If new tools don't appear after the MCP client loads a toolset, call directly over stdio with `scripts/konnect-call.mjs` (section 4); don't guess parameters.
- **Outbound data.** Some MCP tools send components, nets, or the whole circuit to remote services. Before using them on a real design, confirm for each tool whether it sends data out, and get the user's consent. A local checkpoint cannot recall data already sent.

## 2. Installation and version pinning

Konnect is developed by mixelpixx, AGPL-3.0, currently beta: <https://github.com/mixelpixx/Konnect>. This repo does not include the executable; it only records the version and how to obtain it.

Why pin versions: Konnect's tool names, parameter schemas, and IPC behavior change between versions, and verification results only hold for the version verified. Node is pinned so the helper script behaves the same on every machine.

| Variable | Meaning | Combination verified 2026-09 |
|---|---|---|
| `<KONNECT_VERSION>`, `<KONNECT_COMMIT>` | Konnect release and commit | 0.12.1, `fa62e1c` |
| `<KICAD_VERSION>` | KiCad and `kicad-cli` | 10.0.6 |
| `<NODE_VERSION>` | Node running `konnect-call.mjs` | 24.20.0 |

Keep a version record in your project, for example `tools/konnect/version.json`:

```json
{
  "repository": "https://github.com/mixelpixx/Konnect",
  "version": "<KONNECT_VERSION>",
  "commit": "<KONNECT_COMMIT_FULL_SHA>",
  "release": "https://github.com/mixelpixx/Konnect/releases/tag/v<KONNECT_VERSION>",
  "asset_url": "<RELEASE_ASSET_URL>",
  "archive_sha256": "<SHA256_OF_ASSET>",
  "executable": "<GITIGNORED_TOOLS_DIR>/konnect-v<KONNECT_VERSION>/konnect.exe",
  "license": "AGPL-3.0",
  "verified_kicad": "<KICAD_VERSION>"
}
```

1. Download the official asset for your platform from the release page, compute its SHA256, compare it with the digest shown on the GitHub release, and write it into the version record.
2. Extract it to a tools directory excluded by `.gitignore`. When changing machines, re-download and verify per the version record; don't copy executables of unknown origin.
3. Don't run `konnect init`; it writes Konnect's skills/agents into the client config directory and may conflict with your existing skills and hooks. Also don't double-click Konnect or run it directly in an interactive terminal: in the 0.12.1 source, it enters the install flow when stdin is a terminal. Let the MCP client launch it over stdio.
4. Copy the config file from `scripts/konnect/config.example.toml` and fill it in. Always launch with `--config <absolute path>`: without `--config`, Konnect uses the first config file it finds in the working directory, next to the executable, or in the user config directory, which can easily pick up the wrong config. Don't set `project_dir`; pass exact absolute paths on every call.
5. Register it with the client. Claude Code uses the project `.mcp.json`; Codex uses `~/.codex/config.toml`:

```json
{"mcpServers": {"konnect": {"type": "stdio", "command": "<ABS_PATH_TO_KONNECT_EXE>",
  "args": ["--config", "<ABS_PATH_TO_CONFIG_TOML>"]}}}
```

```toml
[mcp_servers.konnect]
command = '<ABS_PATH_TO_KONNECT_EXE>'
args = ['--config', '<ABS_PATH_TO_CONFIG_TOML>']
startup_timeout_sec = 30
tool_timeout_sec = 120
```

These two files contain local absolute paths; don't commit them to a public repo. After changing the config, a running client won't replace an already loaded server; restart the client and then confirm with `get_installation_info`.

## 3. Konnect operation order

1. **Confirm the target.** Read the project README and WORKLOG, confirm there is a single writer and a complete recoverable copy (section 6), and list the exact absolute paths to pass in.
2. **`get_installation_info`.** Check version, commit, executable path, `kicad.version`, and `configuration.source=explicit_path`. A standalone install reporting `installation.source=unknown` is normal; the origin is instead proven by the asset's SHA256.
3. **Load tools.** `list_toolboxes` → `load_toolset({name})` → fetch `tools/list` again, and go by the actual input schema.
4. **Read.** `get_project_info`, `list_schematic_components` (`sch_components`), `get_board_info` (`pcb_board`).
5. **Schematic editing.** Use `sch_components`, `sch_wiring`, `sch_hierarchy`. After saving, run native netlist, ERC, and file diff. If the schematic is already open in the GUI, reconcile the disk and GUI versions first so the GUI's stale buffer doesn't overwrite the new file.
6. **Live PCB editing.** Open the exact target file in the PCB Editor and enable the KiCad API (Preferences → Plugins → Enable KiCad API; this changes KiCad's general settings, so back up the settings file first). Call `open_project({path: <ABS_PCB>})` and confirm the reply has `requested_open=true`. `get_editor_state` (`editor_navigation`) must succeed; read `ipc_available`, `ipc_failure`, and whether the open document is the target.
7. **Read back after every change.** Only a reply with `source=ipc` counts as a live operation. `source=file` means the tool fell back to the file on disk; that is an offline change and cannot be accepted as IPC verification.
8. **DRC.** MCP `run_drc` (`verification`) by default checks only the file on disk. Unsaved GUI changes must be saved first, or use `sync_live_board` explicitly. The final verdict still uses native `kicad-cli pcb drc` (section 5).

| Reply | Meaning | Action |
|---|---|---|
| `isError=true` | Call failed | Stop, save the reply, find the cause |
| `isError=false` | Only means the call replied | Read the inner result: `success`, `source`, `ipc_available`, rejection or diagnostic messages |
| Toolset-not-loaded error | The tool's toolset isn't loaded yet | The error names the toolset; `load_toolset` and call again |
| `source=ipc` | Changed the live board in the GUI | Can be called a live operation; the file on disk is unchanged until saved |
| `source=file` | Changed the file on disk | Treat as an offline change; if the GUI has the same file open, it needs reloading |
| Timeout, unclear result, failed change | State unknown | Check the file and transaction state first; don't automatically resend the change |

Capability table (Konnect 0.12.1, verified 2026-09 on a complete project copy and test projects):

| Task | Konnect tools | Verification level |
|---|---|---|
| Create/modify schematic | `create_project`, `add_schematic_component`, `connect_pins`, `edit_schematic_component` | Passed on a small test project; native netlist confirmed connections and value changes |
| Read project and schematic | `get_project_info`, `list_schematic_components` | Reading a complete project copy passed |
| Offline component move | `move_component`, `get_component_pads` | Moved and moved back; native geometry snapshot and PCB file hash both matched the original |
| Live component read/move | `get_component_list`, `pcb_components` | IPC read and move passed; GUI Undo can revert |
| Single track segment | `route_trace`, `query_traces`, `delete_trace` | Added one segment over IPC, then deleted by UUID; readback consistent. Not an acceptance of obstacle avoidance or autorouting |
| ERC/DRC | `sch_export`, `verification` | Consistent with native CLI baseline results |
| Gerber/drill/BOM/CPL | `pcb_export` | Produces files; default Gerber excludes Paste layers, generic BOM/CPL doesn't include the fab's assembly rules |
| Auto-placement | `placement` | Not verified; not equivalent to other tools' placement DSL |
| Autorouting | `pcb_export`'s Specctra DSN + Freerouting | Not verified. That version's DSN export is limited to 2 copper layers, and the board must not already have tracks, vias, or copper pours |
| Snapshot | `snapshot_project` | Only produces a PDF |

## 4. stdio call script

`scripts/konnect-call.mjs` uses only Node built-in modules. It starts Konnect, loads toolsets in order, calls tools, and writes all replies and the server stderr as JSON.

```sh
export KONNECT_EXE=<ABS_PATH_TO_KONNECT_EXE>       # PowerShell: $env:KONNECT_EXE = '...'
export KONNECT_CONFIG=<ABS_PATH_TO_CONFIG_TOML>
node scripts/konnect-call.mjs request.json response.json
```

You can also use the `--exe` and `--config` arguments; `--timeout <ms>` adjusts the per-call timeout (default 120000). `--help` lists all options.

```json
{"toolsets": ["sch_components", "pcb_board"], "listTools": true,
 "calls": [{"name": "get_board_info", "arguments": {"board": "<ABS_DIR>/board.kicad_pcb"}},
           {"name": "list_schematic_components", "arguments": {"schematic": "<ABS_DIR>/board.kicad_sch"}}]}
```

- The first time, use `"listTools": true` to get the actual schema, then write the calls.
- On `isError` it stops by default and saves the results so far; `"continueOnError": true` keeps going.
- response.json contains local paths and server logs; clean it up before making it public.

## 5. kicad-cli commands

First run `kicad-cli version` and `kicad-cli <subcommand> --help`, and go by the flags of the installed version. The flags below were confirmed on KiCad 10.0.6. `<P>` is the project file name and `out/` is the output directory; don't point it into a fixed release package.

```sh
kicad-cli sch erc --severity-all --exit-code-violations --format json -o out/erc.json <P>.kicad_sch
kicad-cli pcb drc --severity-all --all-track-errors --schematic-parity --exit-code-violations \
  --format json -o out/drc.json <P>.kicad_pcb
kicad-cli sch export netlist --format kicadxml -o out/schematic.net <P>.kicad_sch   # compare before and after changes
kicad-cli sch export pdf -o out/schematic.pdf <P>.kicad_sch
# Gerber: list layers explicitly and include Paste; for 2-layer boards remove In1.Cu, In2.Cu
kicad-cli pcb export gerbers -o out/gerbers/ --use-drill-file-origin \
  --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts <P>.kicad_pcb
# Drill: plot means the drill/place file origin, consistent with the Gerber origin above
kicad-cli pcb export drill -o out/gerbers/ --drill-origin plot --excellon-separate-th \
  --generate-map --map-format pdf --generate-report --report-path out/drill-report.txt <P>.kicad_pcb
kicad-cli pcb export pos --format csv --units mm --side front --use-drill-file-origin --exclude-dnp \
  -o out/cpl.csv <P>.kicad_pcb
kicad-cli sch export bom --fields "Reference,Value,Footprint,QUANTITY,DNP" --group-by Value,Footprint \
  --exclude-dnp -o out/bom.csv <P>.kicad_sch
kicad-cli pcb export pdf --mode-single --layers F.Cu,F.SilkS,Edge.Cuts -o out/top.pdf <P>.kicad_pcb
```

The CLI's BOM/CPL is raw data. The fab's required column names, part number fields, rotation corrections, single-side-only assembly, and similar rules are handled separately and checked against the fab's preview.

| Command or flag | Changes design files? |
|---|---|
| `pcb drc --refill-zones` | Per help, refills in memory and checks without writing back; results may differ from the fills saved in the file |
| `pcb drc --refill-zones --save-board` | **Does** write the refilled board back to `.kicad_pcb` |
| `pcb export gerbers`/`pdf` with `--check-zones` | Refills if needed before plotting; whether it writes back is unverified, so use only on a working copy |
| `pcb upgrade`, `sch upgrade` | **Does** rewrite the file format |
| Other `export`, `erc`, `drc` | Only write the output given by `-o` |

- Run commands containing `--save-board` only on a working copy. Never run them in read-only reviews or on fixed release packages, and don't apply commands from history records directly to the real board. Always review on a throwaway copy and compare hashes before and after.
- After changes, refill and save on the working copy with `pcb drc --refill-zones --save-board --all-track-errors --severity-all --exit-code-violations` (add `--schematic-parity` for a single board; a panel has no corresponding schematic, so leave it out), then run it again to confirm the second refill makes no difference.
- In restricted environments, kicad-cli may report errors on stderr because it can't write to user settings or the Windows registry. Point `KICAD_CONFIG_HOME` and `KICAD_DOCUMENTS_HOME` at a writable temp directory, and judge the result by exit code and output files.

## 6. Before and after changing a PCB

Before changing:

1. Make a complete recoverable backup: the whole project directory, including project-relative libraries, `sym-lib-table`/`fp-lib-table`, `.kicad_dru`, export scripts, and settings. Pack it as a ZIP with a per-file SHA256 list, and unpack it once to compare. A hash list alone is not a backup; a newly created Git worktree also doesn't contain uncommitted changes.
2. Make changes in the working copy (candidate); don't touch the fixed release package.
3. An initial board-generation script that builds the board from scratch rebuilds the whole board and must never be run on a routed, finished board. The entry point for changes is the native file.

After changing:

1. Compare the native netlist with the one before the change; only expected differences should appear.
2. ERC, full DRC (with `--schematic-parity`, `--all-track-errors`), unconnected count.
3. Check counts of nets, footprints, tracks/vias, zones, and the file diff.
4. Regenerate manufacturing outputs and update the hash list.
5. Passing ERC/DRC does not mean electrically correct, accepted by the fab, or that the real board works. Pinouts, RF, power, and component values must be checked against manufacturer documentation.

## 7. Known pitfalls

- **Tool list doesn't refresh.** Some MCP clients don't re-read `tools/list` after `load_toolset`, so the new tools can't be called. Use the stdio script, or set `eager_toolsets = true` to load everything at startup (the tool list gets much larger; this option is not yet tested).
- **IPC not ready.** When Konnect can't find the IPC socket it warns at startup: live tools will fail, and tools that take a file path write to the file on disk instead. Errors like `AS_NOT_READY` usually mean the PCB Editor hasn't opened the target yet, or the API isn't enabled yet.
- **Non-ASCII paths.** KiCad CLI and Konnect tested fine with paths containing Chinese, but other toolchains on the same machine (MinGW, Arduino-Pico) fail on non-ASCII temp or build paths. When you hit a failure with no message, retry with an ASCII temp directory, but don't assume the path was the cause.
- **Restricted shell.** A sandbox may make KiCad user settings or Konnect's transaction/log directories inaccessible. Don't loosen permissions for this, and don't describe a sandbox-caused failure as the tool passing.
- **Claude Desktop on Windows.** It installs as an MSIX package, and writes by its child processes to `%LOCALAPPDATA%` are redirected, so Codex and other programs can't see them. Put caches shared across agents in a directory that isn't redirected.
- **User preferences.** Global defaults read by `load_user_config` (for example a fab's 2-layer rules) aren't necessarily right for the current board; don't apply them directly.
- **Autorouting.** Don't rip up existing tracks or copper pours just to satisfy exporter limitations.

## 8. Switching MCP servers and restoring

- When you need features from another KiCad MCP server (the source project keeps [kicad-copilot](https://github.com/biosshot/kicad-copilot) as the exception entry point for full autorouting): first finish writes from the current server and secure a complete copy, disable the current server, enable the other one, restart the client, and switch back when done. Two servers never write the same design at the same time. Some kicad-copilot tools send design data to remote services, so the outbound data rule in section 1 applies.
- When restoring settings, restore only the MCP sections changed this time. Don't overwrite with an older full client config, or you'll wipe out other settings added in the meantime.
