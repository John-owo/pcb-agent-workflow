# 新手入門：從零做出第一塊 PCB

給第一次做 PCB 的人。照這份走，會從安裝 KiCad 一路做到在 JLCPCB 下單。每一步寫三件事：你要做什麼、可以請 agent（Claude Code 或 Codex）做什麼、怎麼確認做對了。

先說清楚這份指南的範圍：

- **走到下單為止。** 這套流程來自一塊已經下單、但還沒有實板測試的 GNSS 板（見 [examples/](../examples/max-m10s-breakout-revc/README.md)）。到板後的上電與測試還沒寫，等實板驗證後再補。
- **那塊範例板不適合當第一塊板來模仿。** 它是 4 層、含 RF 天線，屬於進階設計。讀它是為了看完整發行包長什麼樣子，不是照著畫。
- **agent 是助手，不是設計者。** 它能查資料、解釋錯誤、檢查檔案、起草文件；結論要對照原廠 datasheet，按下付款或送單的一定是你。
- 看不懂的詞查 [術語表](glossary.md)。

## 0. 先把第一塊板的範圍縮小

第一塊板的目標是「完整走過一次流程、拿到能用的板子」，不是做出最厲害的功能。建議：

| 項目 | 第一塊板建議 | 原因 |
|---|---|---|
| 層數 | 雙層 | 便宜，KiCad 預設就是雙層，規則簡單 |
| 尺寸 | 一張名片以內 | 便宜；太小反而會遇到組裝尺寸限制 |
| 元件 | 0805 以上的電阻電容，或直插件 | 好手焊，出錯好修 |
| 料號 | 優先用 JLC 的 Basic 料 | Extended 料每種另收換料費（2026-10 觀察） |
| 組裝 | 只做 PCB 自己焊，或只貼單面 | 雙面貼裝要選 Standard 組裝，較貴（2026-09 觀察，見 [jlc-ordering.md](workflow/jlc-ordering.md)） |
| 避開 | RF／天線、高速訊號、鋰電池充電、市電（AC 220 V／110 V） | 這些需要經驗，出錯可能危險 |

範例題目：USB-C 供電＋LED＋按鍵、某顆感測器模組的轉接板、Arduino／Pico 的擴充板。

**可以請 agent：**

> 我想做一塊 <功能> 的板子，第一版只用雙層、JLC Basic 料、單面貼裝。先幫我列出需要哪些功能區塊，以及每一塊可以參考哪份原廠 datasheet 或參考設計。不要開始畫，也不要改任何檔案。

## 1. 準備環境

| 工具 | 必要性 | 用途 |
|---|---|---|
| [KiCad](https://www.kicad.org/download/) 10 | 必要 | 畫原理圖與 PCB、匯出製造檔。本 repo 在 10.0.6 驗證過指令 |
| Git | 強烈建議 | 每完成一步就 commit，改壞了可以回到上一步 |
| Claude Code 或 Codex | 建議 | 本 repo 的流程是寫給 agent 協作用的 |
| Python 3.12 | 讓 JLC 貼裝時必要 | 跑 BOM／CPL 檢查腳本（第 7 步）。只做 PCB 自己焊可以不裝 |
| [kicad-happy](https://github.com/aklofas/kicad-happy) skills | 選用 | 讓 agent 分析原理圖、BOM、DRC |
| Konnect MCP | **新手不需要** | 讓 agent 直接操作 KiCad，目前是 beta，見 [kicad-tools.md](workflow/kicad-tools.md) |

再把本 repo 下載到電腦上，放在**你的 PCB 專案資料夾之外**，例如兩者並排：

```bash
git clone https://github.com/John-owo/pcb-agent-workflow.git
```

沒有裝 Git 的話，也可以在 GitHub 頁面用 Code → Download ZIP 下載後解壓縮。下面寫 `<pcb-agent-workflow>` 的地方，代表這個資料夾的路徑。

**確認做對了：** 終端機執行 `kicad-cli version` 能印出版本號。Windows 若找不到指令，KiCad 的 `bin` 資料夾可能沒有加進 PATH，可以請 agent 協助找出安裝位置。

## 2. 開新專案

1. KiCad：File → New Project，選一個**只放這個專案**的資料夾。
2. 把 `<pcb-agent-workflow>/templates/` 裡的 `AGENTS.md`、`CLAUDE.md`、`WORKLOG.md`、`README.md` 複製進去，`<...>` 換成自己的內容；把 `templates/kicad-project.gitignore` 複製進去並改名成 `.gitignore`。
3. 在資料夾裡執行 `git init`，做第一個 commit。

之後每次開新的 agent 對話，它會從 `README.md` 和 `WORKLOG.md` 讀起，知道做到哪裡。

## 3. 畫原理圖

1. **每一塊電路都從原廠資料開始。** IC 的 datasheet 通常有「Typical Application」電路，列出需要的外部元件和數值。照它畫，不要憑印象。
2. 放 symbol、拉線、標網路名稱。電源與 GND 用 power symbol。
3. 每顆要貼裝的零件，在 symbol 加一個名為 `LCSC` 的欄位，填 LCSC 料號（例如 `C25804`）。第 7 步匯出 BOM 時會用到這個欄位名稱。
4. 不貼的零件（例如測試點）設成 DNP（Do Not Populate）。
5. 執行 ERC（Inspect → Electrical Rules Checker），每個錯誤都要看懂再處理。

**可以請 agent：**

> <MPN> 的 datasheet 典型應用電路需要哪些外部元件？列出數值、用途和 datasheet 的頁碼。

> 跑 `kicad-cli sch erc`，把每個錯誤用白話解釋給我聽，說明可能的修法，先不要改檔。

**確認做對了：** ERC 沒有錯誤；每個 IC 的電源腳都有去耦電容；你能說出每顆零件的數值是從哪份資料來的。

## 4. 選料與 footprint

1. 在 [LCSC](https://www.lcsc.com/) 或 JLC 的零件庫搜尋，記下 C 開頭的料號（C-code）。看三件事：封裝尺寸、庫存、是 Basic 還是 Extended。
2. 每顆零件的 footprint 要和**買的那顆料**的 datasheet 尺寸一致。同樣叫 SOT-23，不同廠商的腳位定義可能不同；排針、接頭的方向也要對。
3. KiCad 內建庫找不到的 footprint，可以從原廠或 LCSC 頁面取得，放進**專案自己的**元件庫（路徑用 `${KIPRJMOD}`），不要只放在本機全域庫。

**可以請 agent：**

> 幫我在 LCSC 找 0805、10 kΩ、1% 的 Basic 料，列出 C-code、庫存與查詢日期。

> 比對 U1 的 footprint 腳位和 <MPN> datasheet 的 pinout，逐腳列出是否一致，附 datasheet 頁碼。

**確認做對了：** 每顆貼裝零件都有 C-code；pin 1、極性元件（二極體、LED、電解電容）的方向，你自己對照過 datasheet。

## 5. 設定板子規則

在 PCB Editor 開啟 File → Board Setup（板子設定），在 Design Rules 的 Constraints 與 Net Classes 填入下表。選單名稱以你安裝的版本為準。

| 項目 | 新手建議值 | JLC 雙層能力頁（2026-10 觀察） |
|---|---|---|
| 訊號線寬 | 0.25 mm | 最小 0.10 mm |
| 線距（clearance） | 0.2 mm | 最小 0.10 mm |
| 電源線寬 | 依電流用 KiCad 內建 Calculator Tools 的 Track Width 計算，至少 0.5 mm | — |
| Via 鑽孔／外徑 | 0.3 mm／0.6 mm | 鑽孔 0.2–0.25 mm 搭配外徑小於 0.45 mm，或鑽孔 0.15 mm 以下，會加價 |
| 銅到板邊 | 0.5 mm | 最小 0.2 mm |
| 絲印字高／線寬 | 1.0 mm／0.15 mm | 字高 1.0 mm、線寬 0.15 mm 以上 |

建議值刻意比能力頁寬鬆：第一塊板優先好做、好修，不追求極限。能力會變動，下單前以 [JLC PCB 能力頁](https://jlcpcb.com/capabilities/pcb-capabilities) 為準。

## 6. 擺件與佈線

1. 先畫板框（Edge.Cuts），放固定位置的東西：接頭、按鍵、安裝孔。
2. 再放 IC，去耦電容貼近 IC 的電源腳。
3. 手動佈線：先拉電源，再拉訊號。雙層板常見做法是底層大面積鋪 GND。
4. 絲印標上板名、版本、接腳名稱與 pin 1。
5. 執行 DRC（Inspect → Design Rules Checker），沒有錯誤、沒有未連線。

自動佈局、自動佈線在這套流程裡**沒有驗證過**的方案，第一塊板請自己拉線。

**可以請 agent：**

> 依 <pcb-agent-workflow>/docs/first-board-checklist.md 審查目前的原理圖和 PCB，每一項寫「通過／未通過／無法判斷」並附證據，不要改檔。

> 跑 `kicad-cli pcb drc`，解釋每個違規，先不要改檔。

**確認做對了：** [第一塊板檢查清單](first-board-checklist.md) 每一項都看過；ERC、DRC 都沒有錯誤。記得 ERC／DRC 通過不代表電路正確，只代表沒有違反規則。

## 7. 匯出製造檔

Gerber、鑽孔、CPL 的匯出指令見 [kicad-tools.md 第 5 節](workflow/kicad-tools.md#5-kicad-cli-指令)；雙層板把 Gerber 層清單裡的 `In1.Cu`、`In2.Cu` 拿掉。輸出放在專案裡的 `out/` 之類的資料夾，不要覆蓋設計檔。匯出後把 Gerber 與鑽孔檔所在的資料夾壓成一個 zip，這就是要上傳的 Gerber zip。

要讓 JLC 貼裝的話，還需要 BOM 與 CPL，而且欄名要用 JLC 的格式：

| 檔案 | JLC 欄名 | KiCad 的來源 |
|---|---|---|
| BOM | `Comment`、`Designator`、`Footprint`、`LCSC Part #` | Value、Reference、Footprint、第 3 步加的 `LCSC` 欄位 |
| CPL | `Designator`、`Mid X`、`Mid Y`、`Layer`、`Rotation` | 位置檔（pos）的 Ref、PosX、PosY、Side、Rot |

BOM 可以直接用 JLC 欄名匯出，並把料號列入分組，避免料號不同的同值零件被併在一起：

```bash
kicad-cli sch export bom --fields "Value,Reference,Footprint,LCSC" --labels "Comment,Designator,Footprint,LCSC Part #" --group-by "Value,Footprint,LCSC" --ref-range-delimiter "" --exclude-dnp -o out/bom-jlc.csv <專案>.kicad_sch
```

這行指令還沒在 KiCad 10 實測，先執行 `kicad-cli sch export bom --help`，確認這些旗標都存在。`--ref-range-delimiter ""` 是為了關掉連號縮寫：KiCad 預設會把 `R1,R2,R3` 寫成 `R1-R3`，JLC 需要逐一列出，檢查腳本也會擋下縮寫。Windows PowerShell 5.1 不會把空字串 `""` 傳給程式，請改在 Git Bash 或 PowerShell 7.3 以後的版本執行。

CPL 用位置檔匯出後，欄名要改成 JLC 的格式，座標加上單位，例如 `12.5mm`，可以請 agent 轉換。

改好之後執行檢查腳本：

```bash
python <pcb-agent-workflow>/scripts/check_bom_cpl.py --bom out/bom-jlc.csv --cpl out/cpl-jlc.csv
```

它檢查 BOM 與 CPL 的位號是否完全一致、有沒有重複、料號格式、座標與面別。結果是 `PASS`（退出碼 0）、`WARNING`（1，要人看過）、`INCOMPLETE` 或 `ERROR`（2，不能下單）。它**不**檢查旋轉角度、極性、庫存與 footprint 是否正確；這些要在 JLC 的預覽畫面確認。

**可以請 agent：**

> 把 out/ 裡 KiCad 匯出的位置檔改成 JLC 的 CPL 欄名與格式，另存成 cpl-jlc.csv，不要覆蓋原檔，然後跑 <pcb-agent-workflow>/scripts/check_bom_cpl.py 並解釋結果。

**確認做對了：** 用 KiCad 的 Gerber Viewer 打開匯出的 Gerber，每一層都看一次；檢查腳本是 `PASS`，或每個 `WARNING` 都說得出原因。

## 8. 下單

第一塊板有兩條路：

| 路線 | 做法 | 適合 |
|---|---|---|
| A. 只做 PCB | 上傳 Gerber zip，收到空板自己焊 | 元件都是直插或 0805 以上、會用烙鐵 |
| B. Economic PCBA | 再上傳 BOM 與 CPL，JLC 貼單面 | 有小顆 SMD、想省焊接時間 |

下單細節（服務等級、配料核對、送單設定、付款後流程）見 [jlc-ordering.md](workflow/jlc-ordering.md)。幾個新手常踩的點：

- 上傳後在預覽畫面逐顆看 pin 1 與極性方向。
- **Confirm Production file** 選 Yes，工廠改稿前會先給你確認。走路線 B 時，**Confirm Parts Placement** 也選 Yes。
- 上傳、接受條款、送單、付款、下載工廠檔案、確認生產稿或貼裝確認、寄信，每一次都由你決定、你自己按（完整規則見 [jlc-ordering.md](workflow/jlc-ordering.md) 開頭的「誰決定」）。agent 可以幫你核對、起草要問客服的訊息，停在按下按鈕之前。

下單前，把要交給工廠的那一份檔案固定下來（見 [release-package.md](workflow/release-package.md)），之後的問題才對得上版本。

## 9. 等板子與到板後

- 工廠寄來生產稿時，由你下載檔案，再請 agent 依 [production-file-review.md](workflow/production-file-review.md) 協助比對。確認生產稿仍由你決定。
- 到板後的上電與測試，照範例板的 [實測程序](../examples/max-m10s-breakout-revc-tests/README.md) 做。你的板子不同時，至少保留它的前三步：目視檢查短路或錫橋、上電前量電源對地不是短路、第一次上電用有限流功能的電源。

## 接下來讀什麼

| 想知道 | 讀 |
|---|---|
| 名詞是什麼意思 | [glossary.md](glossary.md) |
| 送廠前要檢查什麼 | [first-board-checklist.md](first-board-checklist.md) |
| 跟 agent 協作、交接 | [collaboration.md](workflow/collaboration.md) |
| JLC 下單細節 | [jlc-ordering.md](workflow/jlc-ordering.md) |
| 跟 JLC 客服溝通 | [jlc-support skill](../skills/jlc-support/SKILL.md) |
| 讓 agent 直接操作 KiCad（進階） | [kicad-tools.md](workflow/kicad-tools.md) |
