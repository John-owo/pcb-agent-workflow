# cam-diff：工廠生產稿與原始 Gerber 的逐層比對

把工廠 CAM 改過的生產稿（常含工藝邊、拼板）對齊回你送出的單板 Gerber，逐層找出差異。審查流程與判讀方式見 [docs/workflow/production-file-review.md](../../docs/workflow/production-file-review.md)。

腳本只做分析，不會修改輸入檔，也不會連網。

## 需求

| 腳本 | Python | 套件 |
|---|---|---|
| `render_compare.py` | 3.12 以上（gerbonara 的最低版本） | `gerbonara`、`Pillow` |
| `pixel_compare.py` | 3.8 以上 | `Pillow` |
| `check_inner_removals.py` | 3.8 以上 | `Pillow` |

```
python -m pip install gerbonara pillow
```

建議裝在 venv。gerbonara 會連帶安裝 click、rtree、quart（它自己的 CLI 與檢視器用）。不需要 gerbv，也不需要 KiCad。KiCad 的 Gerber Viewer 適合用來目視複查；要產生帶網路名稱的 `holes.json` 時才需要 KiCad 自帶的 Python（見下方）。

## 三個腳本

| 步驟 | 腳本 | 輸入 | 輸出 |
|---|---|---|---|
| 1 | `render_compare.py` | 原始 Gerber＋鑽孔（資料夾或 zip）、工廠生產稿（資料夾或 zip） | `layer-summary.json`、`<層>-orig.png`、`<層>-cam.png`、`panel-<檔名>.png` |
| 2 | `pixel_compare.py` | 步驟 1 的資料夾 | `<層>-diff.png`、`<層>-comparison.png`、`pixel-summary.json` |
| 3 | `check_inner_removals.py` | 步驟 1 的資料夾，可加 `holes.json` | `<層>-inner-check.png`、`inner-check.json` |

**render_compare.py**
- 依檔名配對圖層。原始端認 KiCad 命名（`*-F_Cu.*`、`*.gtl` 等）；工廠端先認 JLCPCB 生產稿用過的無副檔名檔案（`tl bl l2 l3 ts bs to bo ko drl`），再退回一般副檔名。對不上時用 `--pair 標籤=原始樣式,工廠樣式` 補充或覆寫。
- 找出原始→工廠座標的轉換：`--rotate`（逆時針度數，繞原點，先套用）加平移。平移可以自己給（`--offset 23 17`），或用 `--offset auto` 由鑽孔位置估算。
- 把原始板框（Edge_Cuts 中心線）轉進工廠座標當比較視窗，兩邊在同一視窗、同一解析度（預設 40 px/mm）光柵化。
- 鑽孔一對一配對，列出移動超過 `--moved-tol`（預設 0.005 mm）的孔、工廠缺少的孔、板內多出的孔、板外的孔（通常是工藝邊定位孔），以及原始孔徑→工廠孔徑對照（可看出補償）。
- 每個工廠 Gerber 另外輸出整個工藝框的預覽圖，用來認工藝邊、V-cut、孔處理標記。
- `--check-upload` 給工廠留存的「原送件副本」，比對每個成員檔的 SHA-256，確認工廠拿到的是你的固定版本。

**pixel_compare.py**
- 灰＝兩邊都有，紅＝只在工廠稿（新增），藍＝只在原始檔（移除）。超過容差的變動用橘框標出。
- `pixel-summary.json` 列出每層新增／移除面積（全部與超過容差兩種），以及每個變動區域的中心，同時給工廠座標與原單板座標。寫信給工廠時用原單板座標。
- 「畫出來的部分」在銅層是銅，在阻焊層是開窗，在絲印層是油墨。

**check_inner_removals.py**
- 對每個孔，在原始圖上從孔心往外填滿相連的銅。填不出 `--max-pad-mm` 方框、且只含一個孔的，視為該層未使用的孤立焊盤；其他視為有連接。
- 工廠移除的銅只有落在孤立焊盤內才算預期的處理（內層刪除非功能焊盤）。其他地方被移除、或有連接的焊盤中心銅不見，都列為可疑。
- 用 `--holes` 帶入網路名稱時，可加 `--plane-nets GND`，列出平面網路上失去中心銅的孔。

## 用法

```
python render_compare.py --original release/gerbers.zip --factory factory/production.zip --offset auto --out out
python pixel_compare.py --renders out
python check_inner_removals.py --renders out
```

常用選項：

| 選項 | 用途 |
|---|---|
| `--offset auto` / `--offset DX DY` | 平移量（mm）。拼板有多個相同單板時，auto 會列出其他候選位置，請逐一用 `--offset` 指定 |
| `--rotate 90` | 工廠把板子轉了方向時使用，逆時針度數 |
| `--pair In1_Cu=*-In1_Cu.*,l2` | 新增或覆寫圖層配對；鋼網檔另外提供時也用它比錫膏層 |
| `--margin 0.5` | 視窗往外多看 0.5 mm，用於板邊附近的改動 |
| `--ppmm 80` | 提高解析度（記憶體與時間約按平方增加） |
| `--check-upload 原送件副本.zip` | 比對工廠留存的原送件與你的固定包 |

先拿同一份 Gerber 自我比對，確認環境正常（預期：偏移 (0, 0)、所有孔配對且誤差 0、每層差異都是 0）：

```
python render_compare.py --original gerbers.zip --factory gerbers.zip --out selftest
python pixel_compare.py --renders selftest
```

### 用 KiCad 產生帶網路名稱的 holes.json

用 KiCad 自帶的 Python 執行（Windows 例：`"C:\Program Files\KiCad\10.0\bin\python.exe"`）。座標換成 Gerber 座標：以 drill/place 原點為準、Y 軸向上。如果出 Gerber 時沒有勾選使用該原點，把 `o` 改成 (0, 0)。

```python
import json, sys, pcbnew
board = pcbnew.LoadBoard(sys.argv[1])
o = board.GetDesignSettings().GetAuxOrigin()
ox, oy = pcbnew.ToMM(o.x), pcbnew.ToMM(o.y)
def xy(p): return round(pcbnew.ToMM(p.x) - ox, 4), round(oy - pcbnew.ToMM(p.y), 4)
holes = []
for t in board.GetTracks():
    if t.GetClass() == "PCB_VIA":
        x, y = xy(t.GetPosition()); holes.append({"x": x, "y": y, "net": t.GetNetname()})
for fp in board.GetFootprints():
    for pad in fp.Pads():
        if pad.HasHole():
            x, y = xy(pad.GetPosition())
            holes.append({"x": x, "y": y, "net": pad.GetNetname(), "ref": fp.GetReference() + "-" + pad.GetNumber()})
json.dump(holes, open(sys.argv[2], "w", encoding="utf-8"), indent=1)
```

## 限制

- 解析度：40 px/mm 時一個像素 0.025 mm，預設容差 1 像素。小於約 0.03 mm 的形狀變化（例如銅箔補償）不會列為超過容差。孔位比對是數值計算，不受此限，小幅移孔要看 `layer-summary.json` 的 `drills.moved`。
- 只看圖形，不懂網路。不能證明連通性，也不能取代工廠的網表比對或電測；`check_inner_removals.py` 是光柵上的啟發式判斷。
- 不做 DRC：不檢查間距、環寬、阻焊橋是否符合製程能力。
- 轉換只支援旋轉加平移，不支援鏡像與縮放。底層 Gerber 本來就是頂視座標，不需要鏡像。
- 圖層配對靠檔名。對不上的層會記在 `layer-summary.json` 的 `notes`，請確認沒有漏比。
- 解析依賴 gerbonara；解析警告數量記在 `layer-summary.json`。省略參數的圓弧等格式問題可能讓絲印有小差異，先排除解析問題再當成工廠改動。
- 外形層的線寬常與原始不同（工廠繪圖線較粗），外形差異以板尺寸和 V-cut 標註判讀，不看像素面積。
- 不解讀 ODB++、V-cut 語意、孔處理標記（如 `sk`）或拼板工序。這些要看圖面標註並問工程。
- 不檢查 PCBA 貼裝；貼裝座標與極性依流程文件人工核對。

## 隱私

輸出的 JSON 會記錄工廠檔案的成員名稱與雜湊，檔名可能含訂單編號；PNG 是工廠的生產資料。輸出留在私有目錄，不要提交到公開 repository。
