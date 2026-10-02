# KiCad 工具：原生 CLI 與 Konnect MCP

說明 agent（Claude Code、Codex）操作 KiCad 10 設計時的工具分工、版本固定、Konnect 呼叫順序、`kicad-cli` 指令，以及修改 PCB 前後的檢查。內容整理自一個已交 JLCPCB 製造的專案；版本與觀察都標了時間，使用前以你安裝的版本重新確認。

## 1. 工具分工

| 工作 | 工具 | 說明 |
|---|---|---|
| ERC、DRC、schematic parity | `kicad-cli` | 判定以原生 CLI 結果為準 |
| Gerber、鑽孔、BOM、CPL、PDF | `kicad-cli` 或專案自己的匯出腳本 | MCP 匯出只作輔助，不當製造交付檔 |
| 讀專案、原理圖、板子資訊 | Konnect | 讀回時看 `source` 欄位 |
| 原理圖編輯 | Konnect `sch_*` toolsets | 保存後用原生 netlist、ERC、檔案差異核對 |
| 即時 PCB 編輯 | Konnect，經 KiCad IPC | GUI 需開著精確目標並啟用 API（第 3 節） |
| 原理圖更新到 PCB | KiCad GUI「Update PCB from Schematic」 | Konnect 的同步功能尚未驗證 |
| 自動佈局、自動佈線 | 沒有驗證過的等價方案 | 見第 3 節能力表與第 8 節 |
| 電氣分析（EMC、SPICE、datasheet） | 分析類 skills + 原生 CLI | 不依賴 MCP |
| 備份 | 完整專案複本，或經檢查的 commit | `snapshot_project` 只產 PDF，不是備份 |

- **單一寫入者。** 同一份設計同時只有一個寫入者：一個 agent、一個 MCP server，或正在操作 GUI 的使用者。使用者在操作 KiCad 視窗時，agent 停止 UI 輸入，等使用者明確通知再繼續。
- **stdio 備援。** MCP client 載入 toolset 後沒出現新工具時，用 `scripts/konnect-call.mjs` 直接以 stdio 呼叫（第 4 節），不要猜參數。
- **外送資料。** 有些 MCP 工具會把元件、網路或整張電路送到遠端服務。對正式設計使用前，逐一確認工具是否外送，並取得使用者同意。本地 checkpoint 撤不回已送出的資料。

## 2. 安裝與版本固定

Konnect 由 mixelpixx 開發，AGPL-3.0，目前是 beta：<https://github.com/mixelpixx/Konnect>。本 repo 不附執行檔，只記錄版本與取得方式。

固定版本的原因：Konnect 的工具名稱、參數 schema 與 IPC 行為會隨版本改變，驗證結果只對驗證時的版本成立。Node 固定是為了讓輔助腳本在每台機器行為一致。

| 變數 | 意義 | 2026-09 驗證過的組合 |
|---|---|---|
| `<KONNECT_VERSION>`、`<KONNECT_COMMIT>` | Konnect release 與 commit | 0.12.1、`fa62e1c` |
| `<KICAD_VERSION>` | KiCad 與 `kicad-cli` | 10.0.6 |
| `<NODE_VERSION>` | 執行 `konnect-call.mjs` 的 Node | 24.20.0 |

在你的專案放一份版本紀錄，例如 `tools/konnect/version.json`：

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

1. 從 release 頁下載對應平台的官方 asset，計算 SHA256，與 GitHub release 標示的 digest 比對後寫入版本紀錄。
2. 解壓到 `.gitignore` 排除的工具目錄。換機時依版本紀錄重新下載並驗證，不拷貝來源不明的執行檔。
3. 不執行 `konnect init`，它會把 Konnect 的 skills／agents 寫進 client 設定目錄，可能和你既有的 skills、hooks 衝突。也不要雙擊或在互動終端直接執行 Konnect：0.12.1 的原始碼在 stdin 是終端機時會進入安裝流程。交給 MCP client 以 stdio 啟動即可。
4. 設定檔從 `scripts/konnect/config.example.toml` 複製後填入。啟動時一律加 `--config <絕對路徑>`：沒給 `--config` 時，Konnect 會採用工作目錄、執行檔旁、使用者設定目錄中第一個找到的設定檔，容易讀到別的設定。不設 `project_dir`，每次呼叫都傳精確的絕對路徑。
5. 註冊到 client。Claude Code 用專案 `.mcp.json`，Codex 用 `~/.codex/config.toml`：

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

這兩個檔含本機絕對路徑，不要提交到公開 repo。改了設定，執行中的 client 不會換掉已載入的 server；重啟 client 後再用 `get_installation_info` 確認。

## 3. Konnect 操作順序

1. **確認目標。** 讀專案 README 與 WORKLOG，確認唯一寫入者、已有完整可恢復副本（第 6 節），列出要傳入的精確絕對路徑。
2. **`get_installation_info`。** 核對版本、commit、執行檔路徑、`kicad.version`，以及 `configuration.source=explicit_path`。standalone 安裝回報 `installation.source=unknown` 是正常的，來源改由 asset 的 SHA256 證明。
3. **載入工具。** `list_toolboxes` → `load_toolset({name})` → 重新取得 `tools/list`，以實際 input schema 為準。
4. **讀取。** `get_project_info`、`list_schematic_components`（`sch_components`）、`get_board_info`（`pcb_board`）。
5. **原理圖編輯。** 用 `sch_components`、`sch_wiring`、`sch_hierarchy`。保存後跑原生 netlist、ERC、檔案差異。原理圖已在 GUI 開啟時，先協調磁碟與 GUI 的版本，避免 GUI 的舊緩衝覆寫新檔。
6. **即時 PCB 編輯。** 在 PCB Editor 開啟精確的目標檔，啟用 KiCad API（Preferences → Plugins → Enable KiCad API；這會改 KiCad 一般設定，先備份設定檔）。呼叫 `open_project({path: <ABS_PCB>})`，確認回覆 `requested_open=true`。`get_editor_state`（`editor_navigation`）必須成功，並讀 `ipc_available`、`ipc_failure`，以及開啟中的文件是否就是目標。
7. **每次修改後讀回。** 回覆 `source=ipc` 才算即時操作。`source=file` 代表工具改用磁碟檔，屬於離線修改，不能當成 IPC 驗收。
8. **DRC。** MCP `run_drc`（`verification`）預設只檢查磁碟上的檔案。GUI 未保存的修改要先保存，或明確使用 `sync_live_board`。最後判定仍用原生 `kicad-cli pcb drc`（第 5 節）。

| 回覆 | 意思 | 處置 |
|---|---|---|
| `isError=true` | 呼叫失敗 | 停下，保存回覆，查原因 |
| `isError=false` | 只代表呼叫有回覆 | 讀內層結果：`success`、`source`、`ipc_available`、拒絕或診斷訊息 |
| toolset 未載入的錯誤 | 工具所屬 toolset 尚未載入 | 錯誤會指出 toolset 名稱，`load_toolset` 後再呼叫 |
| `source=ipc` | 改的是 GUI 中的即時板子 | 可稱即時操作；存檔前磁碟檔不變 |
| `source=file` | 改的是磁碟檔 | 按離線修改處理；GUI 若開著同一檔，需重新載入 |
| 逾時、結果不明、修改失敗 | 狀態未知 | 先查檔案與交易狀態，不自動重送修改 |

能力表（Konnect 0.12.1，2026-09 在完整專案副本與測試專案上驗證）：

| 工作 | Konnect 工具 | 驗證程度 |
|---|---|---|
| 新建／修改原理圖 | `create_project`、`add_schematic_component`、`connect_pins`、`edit_schematic_component` | 小型測試專案通過，原生 netlist 確認連線與改值 |
| 讀專案與原理圖 | `get_project_info`、`list_schematic_components` | 完整專案副本讀取通過 |
| 離線移動元件 | `move_component`、`get_component_pads` | 移動後移回，原生幾何快照與 PCB 檔雜湊皆與原檔相同 |
| 即時讀取／移動元件 | `get_component_list`、`pcb_components` | IPC 讀取與移動通過，GUI Undo 可復原 |
| 單段走線 | `route_trace`、`query_traces`、`delete_trace` | IPC 新增一段再依 UUID 刪除，讀回一致。不是避障或自動佈線驗收 |
| ERC／DRC | `sch_export`、`verification` | 與原生 CLI baseline 結果一致 |
| Gerber／鑽孔／BOM／CPL | `pcb_export` | 能產檔；預設 Gerber 不含 Paste 層，通用 BOM/CPL 不含板廠組裝規則 |
| 自動佈局 | `placement` | 未驗證，與其他工具的佈局 DSL 不等價 |
| 自動佈線 | `pcb_export` 的 Specctra DSN + Freerouting | 未驗證。該版 DSN 匯出限雙銅層，且板上不能已有走線、via、鋪銅 |
| 快照 | `snapshot_project` | 只產 PDF |

## 4. stdio 呼叫腳本

`scripts/konnect-call.mjs` 只用 Node 內建模組。它啟動 Konnect、依序載入 toolset、呼叫工具，把全部回覆與 server stderr 寫成 JSON。

```sh
export KONNECT_EXE=<ABS_PATH_TO_KONNECT_EXE>       # PowerShell: $env:KONNECT_EXE = '...'
export KONNECT_CONFIG=<ABS_PATH_TO_CONFIG_TOML>
node scripts/konnect-call.mjs request.json response.json
```

也可以用 `--exe`、`--config` 參數；`--timeout <ms>` 調整單次逾時（預設 120000）。`--help` 列出全部選項。

```json
{"toolsets": ["sch_components", "pcb_board"], "listTools": true,
 "calls": [{"name": "get_board_info", "arguments": {"board": "<ABS_DIR>/board.kicad_pcb"}},
           {"name": "list_schematic_components", "arguments": {"schematic": "<ABS_DIR>/board.kicad_sch"}}]}
```

- 第一次先用 `"listTools": true` 取得實際 schema，再寫呼叫內容。
- 遇到 `isError` 預設停止並保存已有結果；`"continueOnError": true` 會繼續。
- response.json 含本機路徑與 server log，要公開前先清理。

## 5. kicad-cli 指令

先跑 `kicad-cli version` 與 `kicad-cli <子命令> --help`，旗標以已安裝版本為準。以下旗標在 KiCad 10.0.6 確認過。`<P>` 是專案檔名，`out/` 是輸出目錄，不要指到固定交付包裡。

```sh
kicad-cli sch erc --severity-all --exit-code-violations --format json -o out/erc.json <P>.kicad_sch
kicad-cli pcb drc --severity-all --all-track-errors --schematic-parity --exit-code-violations \
  --format json -o out/drc.json <P>.kicad_pcb
kicad-cli sch export netlist --format kicadxml -o out/schematic.net <P>.kicad_sch   # 修改前後比對
kicad-cli sch export pdf -o out/schematic.pdf <P>.kicad_sch
# Gerber：明確列層並包含 Paste；雙層板拿掉 In1.Cu、In2.Cu
kicad-cli pcb export gerbers -o out/gerbers/ --use-drill-file-origin \
  --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts <P>.kicad_pcb
# 鑽孔：plot 即 drill/place file origin，與上面的 Gerber 原點一致
kicad-cli pcb export drill -o out/gerbers/ --drill-origin plot --excellon-separate-th \
  --generate-map --map-format pdf --generate-report --report-path out/drill-report.txt <P>.kicad_pcb
kicad-cli pcb export pos --format csv --units mm --side front --use-drill-file-origin --exclude-dnp \
  -o out/cpl.csv <P>.kicad_pcb
kicad-cli sch export bom --fields "Reference,Value,Footprint,QUANTITY,DNP" --group-by Value,Footprint \
  --exclude-dnp -o out/bom.csv <P>.kicad_sch
kicad-cli pcb export pdf --mode-single --layers F.Cu,F.SilkS,Edge.Cuts -o out/top.pdf <P>.kicad_pcb
```

CLI 的 BOM／CPL 是原始資料。板廠要求的欄名、料號欄位、旋轉修正與只貼單面等規則，另外處理並以板廠預覽核對。

| 指令或旗標 | 是否改動設計檔 |
|---|---|
| `pcb drc --refill-zones` | 依 help，在記憶體重填後檢查，不寫回；結果可能與存檔中的填銅不同 |
| `pcb drc --refill-zones --save-board` | **會**把重填後的板子寫回 `.kicad_pcb` |
| `pcb export gerbers`／`pdf` 加 `--check-zones` | 必要時重填後出圖；是否寫回未驗證，只在工作副本使用 |
| `pcb upgrade`、`sch upgrade` | **會**改寫檔案格式 |
| 其他 `export`、`erc`、`drc` | 只寫 `-o` 指定的輸出 |

- 含 `--save-board` 的指令只在工作副本執行。唯讀審查與固定交付包絕不執行，歷史紀錄中的指令也不要直接套到正式板。審查一律在拋棄式副本做，前後比對雜湊。
- 修改後在工作副本用 `pcb drc --refill-zones --save-board --all-track-errors --severity-all --exit-code-violations` 重填並存檔（單板加 `--schematic-parity`；拼板沒有對應原理圖，不加），然後再跑一次，確認第二次重填沒有差異。
- 受限環境裡，kicad-cli 可能因寫不進使用者設定或 Windows 登錄檔而在 stderr 報錯。把 `KICAD_CONFIG_HOME`、`KICAD_DOCUMENTS_HOME` 指到可寫的暫存目錄，並以 exit code 與輸出檔判斷結果。

## 6. 修改 PCB 前後

修改前：

1. 建立可恢復的完整備份：整個專案目錄，含專案相對元件庫、`sym-lib-table`／`fp-lib-table`、`.kicad_dru`、匯出腳本與設定。打包成 ZIP 並附逐檔 SHA256 清單，解開比對一次。只有雜湊清單不算備份；新開的 Git worktree 也不含未提交的修改。
2. 在工作副本（candidate）修改，固定交付包不動。
3. 從零產生板子的初始建板腳本會重建整塊板，絕不能對已佈線的成品執行。修改入口是原生檔。

修改後：

1. 原生 netlist 與修改前比對，只出現預期差異。
2. ERC、完整 DRC（含 `--schematic-parity`、`--all-track-errors`）、未連線數。
3. 核對 nets、footprints、tracks／vias、zones 的數量與檔案差異。
4. 重新產生製造輸出並更新雜湊清單。
5. ERC／DRC 通過不代表電氣正確、板廠接受或實板可用。pinout、RF、電源與元件值要對照原廠資料。

## 7. 已知陷阱

- **工具清單不更新。** 有些 MCP client 在 `load_toolset` 後不重讀 `tools/list`，新工具叫不到。用 stdio 腳本；或設 `eager_toolsets = true` 一開始就載入全部（工具清單大很多，這個選項尚未實測）。
- **IPC 未就緒。** Konnect 找不到 IPC socket 時會在啟動時警告：即時工具會失敗，帶檔案路徑的工具改寫磁碟檔。`AS_NOT_READY` 這類錯誤，通常是 PCB Editor 還沒開啟目標，或還沒啟用 API。
- **非 ASCII 路徑。** KiCad CLI 與 Konnect 在含中文的路徑下測試正常，但同機的其他工具鏈（MinGW、Arduino-Pico）遇到非 ASCII 的暫存或建置路徑會失敗。遇到沒有訊息的失敗時，改用 ASCII 暫存目錄重試，但不要直接認定是路徑造成。
- **受限 shell。** 沙箱可能讓 KiCad 使用者設定或 Konnect 的交易／log 目錄無法存取。不要為此放寬權限，也不要把沙箱造成的失敗說成工具通過。
- **Windows 上的 Claude Desktop。** 它以 MSIX 套件安裝，子程序寫入 `%LOCALAPPDATA%` 會被重導，Codex 等其他程式看不到。跨 agent 共用的快取放在不受重導的目錄。
- **使用者偏好。** `load_user_config` 讀到的全域預設（例如板廠的雙層規則）不一定適合目前的板子，不要直接套用。
- **自動佈線。** 不要為了符合匯出器限制而拆掉既有走線或鋪銅。

## 8. 切換 MCP server 與回復

- 需要另一個 KiCad MCP server 的功能時（來源專案保留 [kicad-copilot](https://github.com/biosshot/kicad-copilot) 作為完整自動佈線的例外入口）：先結束目前 server 的寫入並保全完整副本，停用目前的 server、啟用另一個、重啟 client，做完再切回。兩個 server 不同時寫同一份設計。kicad-copilot 的部分工具會把設計資料送到遠端服務，適用第 1 節的外送規則。
- 回復設定時，只還原這次改動的 MCP 區段。不要用較早的整份 client 設定覆蓋，以免蓋掉期間新增的其他設定。
