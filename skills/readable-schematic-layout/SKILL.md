---
name: readable-schematic-layout
description: 把 KiCad 原理圖與 PCB 佈局畫成符合人類習慣、方便除錯的樣子：用 KiCad 內建 symbol、電源 symbol、實際畫線、依電流／訊號流向分區、文字不重疊，佈局對應原理圖分區並留好除錯點。只改畫法時以 netlist 連線分群比對證明電路不變。Use when drawing, redrawing, cleaning up or reviewing a schematic or PCB layout for readability/debuggability — "原理圖好讀", "改成人類畫法", "文字重疊", "用內建 symbol", "方便除錯", "整理原理圖", "layout 好除錯", "readable schematic", "redraw schematic".
---

# 人類好讀、好除錯的原理圖與佈局

目標讀者是拿著電表、示波器除錯的人：看圖就知道電從哪裡來、訊號往哪裡去、該量哪一點。
專案自己的協作規則（單一寫入者、改檔前先保全版本、審查流程）優先；本 skill 只規定「畫法」與「證明沒改到電路」。

## 0. 開工前要問使用者的決策（不要自己決定）

一次問完，答完才動檔：

1. **正本是誰**：程式產生器（腳本輸出 `.kicad_sch`），還是直接編輯 `.kicad_sch`（KiCad GUI、KiCad MCP 或腳本）？改成直接編輯後，產生器要刪除或停用，否則重跑會蓋掉人工修改。
2. **誰操作**：agent（MCP／腳本，不開 GUI）或使用者開 GUI。同一時間只有一位寫入者。
3. **IC 是否換內建 symbol**（有的才換；沒有的重畫自訂 symbol）。
4. **網路名稱**：保留原名（文件、韌體、審查紀錄不用改），或改 KiCad 標準名（`+3V3`）。
5. **跨頁訊號**：頁邊 global label，或 hierarchical label＋根頁連線。
6. **MCP 做不到時的備案**：小腳本直接改文字檔，或停下來問。
7. **審查者**：另一個 agent、唯讀子代理，或使用者目視。

## 1. 原理圖畫法

### Symbol
- 分立元件一律用 KiCad 內建 symbol：MOS `Transistor_FET:<MPN>` 或 `Device:Q_NMOS`/`Q_PMOS`、開關 `Switch:SW_SPDT`/`SW_Push`、電池 `Device:Battery_Cell`、TVS/ESD `Device:D_TVS`（雙向）或 `Power_Protection:*`、天線 `Device:Antenna_Shield`、測試點 `Connector:TestPoint`、R/C/L/LED `Device:*`。不要用畫成方框的自訂 symbol 代表這些元件。
- IC 有內建 symbol 就用（例如 `RF_GPS:MAX-M10S`、`Power_Management:TPS22919DCK`、`Logic_LevelTranslator:SN74LVC1T45DBV`）。查法：在 KiCad 安裝目錄的 `share/kicad/symbols/*.kicad_sym` 搜尋 `symbol "<名稱>`。
- 沒有內建 symbol 的 IC／模組自己畫：電源腳在上、GND 在下、輸入在左、輸出在右；同功能的腳（SPI、UART、電源、控制）排在一起；腳名照規格書；未用腳標 no-connect。
- **換 symbol 一定核對腳號 = footprint 焊盤號**。內建 symbol 的腳號常和自建 footprint 不同（例：SPDT 開關的公共端、電池 +/−、天線饋入／接地）。對不上時換 symbol 或改用自訂 symbol，**不改 footprint、不改連線**；確實要改時先問使用者。
- 換 symbol 時保留位號、值、footprint、Datasheet、Description 與所有自訂欄位（Manufacturer、MPN、供應商料號、DNP 等）。

### 連線與網路
- 電源與地用電源 symbol（`power:GND`、`power:+3V3`…）。保留原網路名稱時，內建庫沒有的名稱（如 `VSYS`）在專案庫做同樣式的電源 symbol；網路名稱由 symbol 的 value 決定，做完要在 netlist 確認名稱正確。
- 電源 symbol 方向固定：正電源朝上、GND 朝下。
- **頁內元件之間實際畫線**，不要每支腳都掛 label。label 只用在跨頁訊號（集中在頁邊的「介面欄」），或線太長會穿越其他區塊時。
- 同一網路不要同時用 label 和不同名稱的電源 symbol。
- 去耦電容畫在所屬 IC 電源腳旁，從腳拉線到電容再到 GND symbol。
- 線不穿過元件本體；T 形接點要有 junction，避免四向交叉接點。
- 未用腳放 no-connect；ERC 需要的 `PWR_FLAG` 放在電源進入點旁。

### 排版
- 依**電流／訊號流向**由左到右：例如 電池 → 保護 → 反接 → 開關 → 系統電源 → 升壓／LDO → 負載；MCU → 位準轉換 → 模組 → RF 前端 → 天線。
- 每個功能區用圖框圈起來並加標題，例如「電池保護」「5V 升壓」。
- 電源在上、GND 在下；同類電路（一排下拉電阻、測試點）排成一列對齊。
- 元件、線、label 放在 50 mil（1.27 mm）格點；symbol 只用 0°／90°／180°／270°。
- **文字不可重疊**：位號、值、label、註解、腳名彼此不重疊，也不壓在線或 symbol 上；值和位號放在 symbol 旁同一側。
- 設計註解（電源開關規則、晶片勘誤、斷電隔離、腳位不接的原因）放在相關電路旁的空白處，必要時加框；不要只留在外部文件。
- 測試點旁標網路名與預期值（例如 `TP1 VBUS_SENSE, 無 USB 時 <0.5 V`）。
- 紙張不夠就換 A3 或拆頁，不要擠。根頁只放子頁方框與簡短的方塊說明。

## 2. PCB 佈局（方便除錯的部分）

電氣與製造規則（RF、阻抗、去耦距離、DFM）以各案設計文件與板廠規範為準；這裡只列除錯習慣。

- 佈局分區對應原理圖分區，按同一個電流流向排；同一功能區的元件放一起。
- 位號依子頁分段（例如 1xx 電源、2xx MCU、3xx 無線、4xx GNSS）；絲印位號清楚、不壓焊盤／過孔，同一面只用兩種讀向。
- 測試點放在探棒碰得到的位置（不在元件下、不被外殼或模組蓋住），絲印標網路名；每條電源軌、致能訊號、關鍵 IO 至少一個測試點或可量的焊盤；接地點要好夾鱷魚夾。
- 極性元件（二極體、電解電容、電池座、LED）絲印標極性；連接器標腳 1 與訊號名；開關標 ON／OFF 方向。
- DNP／選配元件保留焊盤與絲印，在 Fab 層或絲印註明 DNP。
- 在分段除錯點放可斷開的元件（0 Ω、跳線焊盤），方便分別量各電源軌電流。
- 板上放版本、日期、專案名。

## 3. 驗收：證明只改畫法、沒改電路

改圖前先保全（git commit 或完整副本），並把基準 netlist 複製出來。

1. 匯出 netlist：`kicad-cli sch export netlist --format kicadxml -o <new>.xml <root>.kicad_sch`
2. 比對連線分群與元件欄位（腳本在本 skill 目錄的 `scripts/`）：
   `python -I <skill 目錄>/scripts/compare_netlist.py <base>.xml <new>.xml [--names]`
   必須 `IDENTICAL`。保留原網路名稱時加 `--names`。任何差異都要能逐條說明，否則回頭修圖。
3. ERC：`kicad-cli sch erc --severity-all -o erc.rpt <root>.kicad_sch` → 0 錯誤、0 警告。
4. symbol／footprint 腳號：逐件比對 netlist 中每顆元件的腳號集合與其 footprint 的焊盤號集合（專案有現成腳本就用）。
5. 目視：`kicad-cli sch export pdf` → `pdftoppm -r 110 -png` → 逐頁看圖。檢查文字無重疊、線不穿元件、分區清楚、註解都在、流向從左到右。MCP 的重疊偵測工具可輔助，但不能取代目視。
6. 交審查者看固定版本，重點是 netlist 比對結果與可讀性。

以上都通過才能說「畫法改完、電路不變」；這仍不代表電氣正確或實板可用。

## 4. 工具備忘

- 用 KiCad MCP（例如 Konnect）時，先列出並載入原理圖相關工具組（元件、連線、批次、分析、匯出），以實際 schema 為準，不要猜參數。
- MCP 做不到的動作（例如保留自訂欄位換 symbol）改用小腳本直接改 `.kicad_sch` 文字；一樣在檔案沒被 GUI 開啟時進行、一樣走第 3 節驗收。
- 每完成一張子頁就跑一次第 3 節 1–3 步，不要全部畫完才比對。
