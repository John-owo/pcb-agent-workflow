# MAX-M10S 被動天線 GNSS 轉接板（Rev C，OSP，僅頂面組裝）

以 u-blox MAX-M10S 為核心的小型 GNSS 轉接板，接被動式天線，供麵包板或主控板以 UART／I2C 使用。原生設計為 KiCad 10，發行日期 2026-09-21。

## 板子規格

- 尺寸 25.0 × 36.5 mm，4 層，板厚 1.6 mm，表面處理 OSP，疊構按 JLC04161H-7628 設定。
- U1：MAX-M10S-00B，使用預設低增益內建 LNA。
- J1：I-PEX MHF I（20279-001E-03）接被動式 50 Ω 天線，不供天線電源。D1 為天線端 ESD 保護。
- J2、J3：兩支 1×6、2.54 mm 排針，從板底插入，兩排間距 17.78 mm。
- TX／RX／PPS 串 33 Ω，I2C 有 4.7 kΩ 上拉，電源 LED，PPS LED 經 BSS138 緩衝。另有 5 個測試焊盤（TP1、TP2、TP4–TP6）。
- 無 RTC 備援電源：U1 pin 6（V_BCKP）刻意不接，板上沒有電池或超級電容。
- 原理圖註記：UART 9600 8N1，I2C 位址 0x42。

## 接線

- 只接外部穩壓 3.3 V 電源與 3.3 V 邏輯，不耐 5 V。
- 模組 TX → 主控 RX，模組 RX → 主控 TX，並共地。
- 排針由天線端往下：
  - J2：3V3 / GND / TX / RX / PPS / EXTINT
  - J3：GND / SCL / SDA / RESET_N / SAFEBOOT_N / GND
- 沒有備援電源，完全斷電後需由主控重新設定 GNSS。
- 移除 GNSS 電源前先斷開主控訊號。
- PPS LED 閃爍不代表已定位。

## 檔案

| 路徑 | 內容 |
|---|---|
| `MAX-M10S-Passive.kicad_pro` / `.kicad_sch` / `.kicad_pcb` / `.kicad_dru` | KiCad 10 原生專案、原理圖、PCB、自訂設計規則 |
| `fp-lib-table`、`sym-lib-table` | 專案元件庫表，以 `${KIPRJMOD}` 相對路徑指向下兩項 |
| `footprints/PassiveGNSS.pretty/` | 專案 footprint 庫 |
| `symbols/PassiveGNSS.kicad_sym` | 專案 symbol 庫 |
| `design.json` | 元件、網路、料號與 PCB 座標的機器可讀摘要（KiCad 不讀此檔） |
| `manufacturing/gerbers-board.zip` | 單板 Gerber、鑽孔檔與 Gerber job 檔 |
| `manufacturing/BOM-JLCPCB-top-only.csv` | 板廠組裝 BOM：11 組料、每片 17 個元件，含 LCSC 料號 |
| `manufacturing/CPL-board-top-only.csv` | 板廠貼片座標，僅 Top，單板座標 |
| `manufacturing/assembly-orientation.pdf` / `.csv` / `-1.png` | 裝配方向圖與對照表（pin 1、極性端、座標） |
| `manufacturing/BOM-customer-headers.csv` | 自行焊接的排針 J2、J3 |
| `manufacturing/schematic.pdf` | 原理圖 PDF |
| `verification/erc.json`、`drc.json` | 發行時的原生 ERC／DRC 結果 |
| `verification/release-checks.json` | 發行差異核對摘要 |
| `verification/independent-release-review.md` | 獨立審查紀錄（範圍見下文） |

`PassiveGNSS` 庫裡還有 Rev C 板上沒用到的項目：footprint `ADCM_S05R5SA`、`CPH3225A`（已移除的備援電源）、`Fiducial_1mm`、`ToolingHole_2mm`，symbol `BAS116`、`C_Polarized`、`D`。部分 footprint／symbol 衍生自 KiCad 官方元件庫，來源與授權見 repo 的 NOTICE。

## 製造用哪些檔

以下四項是同一套，一起使用，不要和其他版本的檔案混用：

1. `manufacturing/gerbers-board.zip`：製板
2. `manufacturing/BOM-JLCPCB-top-only.csv`：組裝 BOM
3. `manufacturing/CPL-board-top-only.csv`：貼片座標
4. `manufacturing/assembly-orientation.pdf`（另有 `.csv`、`.png`）：裝配方向，用來核對板廠的貼片預覽

補充：

- Gerber 是單板，不含拼板工藝邊和定位點。原發行時的安排是由板廠加工藝邊與定位點、交貨前拆邊；這項服務與做法須由板廠確認。
- 工廠只組裝頂面 17 個元件。J2、J3 排針不在組裝 BOM／CPL 內，依 `BOM-customer-headers.csv` 自行從板底插入焊接（每片 2 支）。原生設計仍保留 J2、J3，作為成品的一部分。
- OSP 板收到後盡早焊排針。

## 已驗證

- **原生 ERC／DRC**（KiCad 10.0.6，發行時 2026-09-21）：ERC 0 項違規；DRC 0 項違規、0 個未連線項目、0 個原理圖／PCB 一致性問題。報告含 error、warning、exclusion 三種等級，見 `verification/`。
- **本副本重跑**（2026-10-02，KiCad 10.0.6 `kicad-cli`，`--severity-all`，DRC 加 `--schematic-parity`）：結果相同。元件庫經 `${KIPRJMOD}` 正常載入，沒有缺 symbol 或 footprint 的警告。這次重跑的輸出沒有放進套件，以免改動發行時的 `verification/`；可以用 [kicad-tools.md](../../docs/workflow/kicad-tools.md) 第 5 節的命令自行重現。
- **發行差異核對**（`release-checks.json`）：與前一版 Rev C 相比，PCB 幾何、走線、焊盤與網路不變。這一版只改了 D1 料號文字、資料表連結、OSP 製造屬性與組裝清單。Gerber ZIP 與當時上傳板廠的檔案逐位元相同。
- **獨立審查**（`independent-release-review.md`）：由唯讀的審查 agent 檢查發行檔案（README、BOM、CPL、裝配表、ERC／DRC 報告等）彼此是否一致，沒有發現致命的不一致或遺漏。審查範圍只到這些檔案的一致性；審查的是原始發行版的 README，本 README 為公開範例重寫，不在審查範圍內。審查者沒有重新開啟或重算 Gerber ZIP，也沒有核對網站狀態、疊構實作、PDF 呈現、電氣／RF／EMC／DFM 行為或實板。

## 未驗證

- ERC／DRC 通過，不代表電路正確、板廠會接受，或實板能正常工作。
- EMC：先前的設計審查只做過 EMC 啟發式分析，留下未經實測的風險提示，例如介面訊號換層處 1 mm 內沒有獨立的 GND stitching via。這些不算通過 EMC，也沒有做過 EMC 測試。
- SPICE：自動模擬因本機模擬器逾時而跳過，沒有 SPICE 通過的結果。
- 這一版只核對交付差異，不是重新做的完整電氣／EMC 驗證。
- 板廠 DFM 審核與貼片確認的結果不在本套件內。板廠的最終生產稿與元件方向須另行確認。
- 兩片組裝板已通過實測程序第 3–7 步；M10S 輔助定位只在實板試過一次回灌（MGA-DBD＋位置）。實測程序與結果見 [max-m10s-breakout-revc-tests](../max-m10s-breakout-revc-tests/README.md)。先前在 NEO-6M 上做的 ALP／AOP 測試，不能當作 M10S 的結果。

## 已知注意事項

- **D1 footprint 名稱與實際料號不同**：footprint 名稱是 `PassiveGNSS:PESD3V3C1BSF`，實際料號是 Nexperia PESD3V3Z1BSFYL（LCSC C2908830）。兩者用同一組焊盤（DSN0603-2／SOD962-2，0.4 mm pitch），footprint 名稱沒改。採購以 BOM 的料號為準。
- **D1 焊盤間距**：依 Nexperia 建議焊盤，兩焊盤實際間距約 0.144 mm，小於專案預設間距（網路類別 0.2 mm）。`.kicad_dru` 對 D1 焊盤之間（0.13 mm）以及 RF 走線到 D1 焊盤（0.15 mm）設了局部規則，另規定 RF 與 GND 鋪銅保持 1.0 mm。
- **Gerber job 檔的表面處理欄位**：`gerbers-board.zip` 內 `MAX-M10S-Passive-job.gbrjob` 的 `Finish` 寫的是 `ENIG`，而 PCB 設定與本版製造規格都是 OSP。Gerber 沒有在改成 OSP 後重新產生，所以下單時要在訂單上選 OSP。
- **J1 座標**：CPL 用的是連接器的機構中心 (15.800, 33.700)，和 RF 接點焊盤 (15.800, 32.175) 位置不同。須確認外殼和中心接點的方向。
- **極性**：元件頂面的標記不一定代表極性。D2、D3、Q1、U1 都要依 `assembly-orientation.pdf` 的 pin 1 和極性端，比對板廠的貼片預覽。
- **design.json 的元件數**：備註寫 19 個元件，這個數字包含自行焊接的 J2、J3；板廠組裝是 17 個。
- 設計時曾和 SparkFun 公開的 MAX-M10S breakout 原理圖逐項比較差異與取捨。本設計的電路與檔案是重新繪製的，沒有複製 SparkFun 的檔案。
- U1 與 J1 的 footprint 依原廠資料建立：MAX-M10S Integration Manual UBX-20053088 R05（焊盤、鋼網開口），I-PEX 20279 圖面 rev.29。這些原廠資料沒有附在本套件內。

## 原廠資料表

原廠資料表、整合手冊和圖面有著作權，不附在本套件內，請到原廠網站下載。下表取自原理圖 symbol 的 Datasheet 欄位：

| 位號 | 料號 | 廠商 | 資料表 |
|---|---|---|---|
| U1 | MAX-M10S-00B | u-blox | https://content.u-blox.com/sites/default/files/MAX-M10S_DataSheet_UBX-20035208.pdf |
| D1 | PESD3V3Z1BSFYL | Nexperia | https://assets.nexperia.com/documents/data-sheet/PESD3V3Z1BSF.pdf |
| Q1 | BSS138 | onsemi | https://www.onsemi.com/pdf/datasheet/bss138-d.pdf |

其他元件（電阻、電容、LED、J1、排針）的 Datasheet 欄位是空的，可依 BOM 上的製造商料號到原廠網站查詢。
