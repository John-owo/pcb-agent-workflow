# Konnect layout tool limitations

**Snapshot: Konnect 0.12.1, observed 2026-10.** If your version differs, first confirm the actual tools and schema with `get_installation_info` and `tools/list`; the behavior below may have changed.

- `update_pcb_from_schematic` skips components whose `in_bom` is no (such as test points); have the user add them by pressing F8 (Update PCB from Schematic) in the GUI instead.
- Footprints placed by sync lose their SMD/THT attribute, pad chamfers and similar content. `update_footprints_from_library` can update them, but cannot handle footprints with rule areas, pad clearances or certain text formats, and also clears the Datasheet and Description fields. Reload these footprints from the library with a pcbnew script while KiCad is closed (compare pad positions and nets before swapping), then restore the fields from the netlist.
- Cannot move designator text; tidy the silkscreen with a pcbnew script while KiCad is closed.
- `add_zone` takes only one at a time; sending two at once makes KiCad return `AS_BUSY`.
- For bulk routing, first compute coordinates with pcbnew on a scratch copy and run DRC; once confirmed, write through MCP, then read back and verify.
