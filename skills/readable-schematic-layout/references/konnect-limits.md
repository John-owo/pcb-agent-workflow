# Konnect 佈局工具限制

**快照：Konnect 0.12.1，2026-10 觀察。** 版本不同時，先用 `get_installation_info` 與 `tools/list` 確認實際工具與 schema；以下行為可能已改變。

- `update_pcb_from_schematic` 會跳過 `in_bom` 為 no 的元件（例如測試點）；改由使用者在 GUI 按 F8（Update PCB from Schematic）補上。
- 同步放入的封裝會遺失 SMD／THT 屬性、焊盤倒角等內容。`update_footprints_from_library` 可以更新，但無法處理含 rule area、焊盤 clearance 或特定文字格式的封裝，也會清掉 Datasheet、Description 欄位。這些封裝在 KiCad 關閉時用 pcbnew 腳本從元件庫重載（換之前比對焊盤位置與網路），再依 netlist 補回欄位。
- 不能移動位號文字；絲印整理在 KiCad 關閉時用 pcbnew 腳本做。
- `add_zone` 一次只送一個；同時送兩個時 KiCad 回 `AS_BUSY`。
- 大量走線先在暫存副本用 pcbnew 試算座標並跑 DRC，確認無誤再經 MCP 寫入，寫入後讀回核對。
