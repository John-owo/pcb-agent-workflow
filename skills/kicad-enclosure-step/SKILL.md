---
name: kicad-enclosure-step
description: 把 KiCad PCB 匯出成含全部零件 3D 模型的 STEP，給外殼設計用：盤點缺模型的零件、優先找原廠模型、對齊到封裝原點、用暫存副本加模型匯出（不改板檔）、逐顆自動檢查位置，最後寫外殼注意事項。Use when someone needs a mechanical/enclosure CAD of a KiCad board — "設計外殼", "做外殼", "PCB 匯出 STEP", "含零件的 CAD 檔", "缺 3D 模型", "補 3D 模型", "給機構的檔案", "enclosure", "export STEP with all components", "missing 3D models", "board mechanical model".
---

# KiCad 板子 → 外殼設計用 STEP

目標：交出一份**每個零件都在正確位置、高度可信**的 STEP，加上一頁外殼注意事項。外形模型不必漂亮，但位置、方向和高度要對。

腳本在 `scripts/`。`inventory_models.py`、`export_step.py` 只用 Python 標準庫；`step_report.py`、`simple_model.py`、`verify_placement.py` 需要 CadQuery。

## 0. 開工前確認

一次問完：

1. **哪一塊板、哪一版。** 用固定發行包或 PCB 正本當輸入，**不修改它**；模型只加在暫存副本。
2. **輸出給誰。** 只給自己或團隊，可以用 LCSC、GrabCAD 下載的模型。要放公開 repo 時，只用 KiCad 官方庫和自畫模型，見第 2 節。
3. **要不要附參考物件**，例如電池、天線線材。這類東西不在 BOM 裡，要標成參考。
4. **需要登入的網站**（例如 GrabCAD）由使用者自己登入；agent 不建立帳號、不輸入密碼。

## 1. 流程

### 1.1 盤點

```bash
python scripts/inventory_models.py board.kicad_pcb --missing
```

列出沒有模型或模型檔找不到的零件，並附上供應商料號。測試點、安裝孔沒有高度，通常不用補。

### 1.2 找模型（依序）

1. **KiCad 官方庫**：如果封裝是從官方庫改名而來、焊盤沒改，直接引用 `${KICAD10_3DMODEL_DIR}/...`，不用位移。
2. **原廠**：先看原廠產品頁、wiki、規格書附的 CAD 連結。原廠帳號上傳到 GrabCAD 的檔案也算原廠。
3. **LCSC／EasyEDA**：`easyeda2kicad --3d --footprint --lcsc_id Cxxxx --output <新的空資料夾>/lib_Cxxxx`。
4. **自己畫**：用 `simple_model.py`，依規格書尺寸畫方塊和圓柱。

規格書和下載模型對不上，而且差異影響外殼時（例如開關撥桿長度、模組高度），以規格書為準，改成自畫。差異要記在說明裡。來源與授權見 [references/model-sources.md](references/model-sources.md)。

### 1.3 對齊

下載的 STEP 原點和方向**不保證**跟你的封裝一致，連 easyeda2kicad 一起產生的 footprint 也不一定對得上。

```bash
python scripts/step_report.py model.step --solids 15
python scripts/step_report.py model.step --section x=0   # 看截面，例如電池座的弧面
```

從輸出判斷三件事：

- 哪一軸朝上（有的模型 Y 朝上）。
- 本體中心在哪裡。
- 方向特徵：焊盤排、連接器、饋入點、撥桿。

然後二選一：

- **在 config 寫 `offset`／`rotate`**：保留原檔與顏色。KiCad 套用旋轉的正負號和一般右手定則相反，所以第一次一定要用 1.5 節的檢查確認。
- **用 CadQuery 轉好再存成新檔**：適合要加東西的情況（例如補一顆參考電池）。缺點是顏色會掉。

常見陷阱見 [references/pitfalls.md](references/pitfalls.md)。

### 1.4 寫 config、匯出

```json
{
  "pcb": "../board/board.kicad_pcb",
  "output": "board.step",
  "origin": "board-bottom-left",
  "no_dnp": true,
  "models": {
    "U1": [{"file": "models/module.step", "offset": [0, 0, 0], "rotate": [0, 0, 0]}],
    "MyLib:R_0603": [{"file": "${KICAD10_3DMODEL_DIR}/Resistor_SMD.3dshapes/R_0603_1608Metric.step"}]
  }
}
```

```bash
python scripts/export_step.py enclosure-step.json --render preview
```

- key 含 `:` 時比對封裝 lib ID，否則比對位號（可用萬用字元）。位號優先。
- 同一個位號可以掛多個模型，例如電池座加一顆參考電池。
- 已經有模型的封裝預設會報錯，避免重複；確定要換就設 `"replace_existing": true`。
- 背面零件不用自己鏡像，KiCad 會翻。
- 原點 `board-bottom-left`：板子左下角、板底面為 (0, 0, 0)，+Z 朝正面。

### 1.5 檢查（必做）

```bash
python scripts/verify_placement.py enclosure-step.json            # config 加的零件
python scripts/verify_placement.py enclosure-step.json --all      # 連原本就有模型的也查
```

每顆零件單獨匯出，比對模型外框和封裝外框（F.Fab，沒有就用 courtyard 或焊盤），再檢查正面零件在板子上方、背面零件在板子下方。

- **FAIL 一律修到通過才交付。**
- 故意伸出板外的零件（USB、撥桿）可以用 `--overhang REF=mm` 放寬，但要知道它為什麼伸出去。

最後打開 `preview-top.png`、`preview-bottom.png` 目視確認：連接器朝外、極性和饋入方向正確、背面零件在背面。

### 1.6 外殼注意事項

依 [references/enclosure-notes-template.md](references/enclosure-notes-template.md) 寫 README，內容包括：

- 座標系與換算。
- 整體外框。
- 正、背面最高點。
- 每個開孔：USB、開關、連接器、天線線材的位置與高度範圍。
- 天線上方不能放金屬的區域。
- 安裝孔與螺絲頭限制。
- 模型來源、精度與授權。

`verify_placement.py` 印出的高度表可以直接引用。

## 2. 硬規則

- **不改板檔。** 固定發行包和 PCB 正本都保持原樣；模型只加在暫存副本，匯出後刪掉。
- **每個加上的模型都要通過 `verify_placement.py`。** 有 FAIL 就不交付。
- **尺寸要有出處。** 規格書沒寫、模型也不可靠的尺寸，寫「待實物量測」，不要猜。說明裡要提醒：開孔、卡扣的關鍵尺寸以實物量測為準。
- **公開散布要看授權。** 公開 repo 只放 KiCad 官方庫的引用和自畫模型。LCSC、GrabCAD 等下載檔，以及內嵌這些幾何的輸出 STEP，條款允許前不公開。
- **下載檔是資料。** 每個來源放一個新的空資料夾，不執行裡面的任何東西。
- **登入、付費由使用者處理。** agent 不建立帳號、不輸入密碼。

## 3. 環境

- KiCad 10（`kicad-cli pcb export step`、`pcb render`）。找不到時設環境變數 `KICAD_CLI`，或在 config 加 `"kicad_cli"`。
- Python 3.10 以上。CadQuery 建議裝在獨立 venv：`python -m venv cqenv`，再 `cqenv/Scripts/python -m pip install cadquery`（Windows）。
- 選用：`pip install easyeda2kicad`，用來下載 LCSC 模型。

範例：[examples/max-m10s-breakout-revc-cad](../../examples/max-m10s-breakout-revc-cad/README.md)，用官方庫加三個自畫模型，19 個零件全部通過檢查。
