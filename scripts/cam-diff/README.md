# cam-diff：工廠生產稿與原始 Gerber 的逐層比對

把工廠 CAM 改過的生產稿（常含工藝邊、拼板）對齊回你送出的單板 Gerber，逐層找出差異。審查流程與判讀方式見 [docs/workflow/production-file-review.md](../../docs/workflow/production-file-review.md)。

腳本只做分析，不會修改輸入檔，也不會連網。

## 需求

| 腳本 | Python | 套件 |
|---|---|---|
| `render_compare.py` | 3.12（固定套件與 CI 使用版本） | `gerbonara`、`Pillow` |
| `pixel_compare.py` | 3.12（固定套件與 CI 使用版本） | `Pillow` |
| `check_inner_removals.py` | 3.12（固定套件與 CI 使用版本） | `Pillow` |

```
python -m pip install -r requirements-cam.txt
```

建議裝在 venv。gerbonara 會連帶安裝 click、rtree、quart（它自己的 CLI 與檢視器用）。不需要 gerbv，也不需要 KiCad。KiCad 的 Gerber Viewer 適合用來目視複查；要產生帶網路名稱的 `holes.json` 時才需要 KiCad 自帶的 Python（見下方）。

安裝命令從 repo 根目錄執行；相依版本（包含間接套件）固定在 `requirements-cam.txt`。更新版本時重跑 `python -m unittest discover -s tests -v`；CI 會在 Python 3.12 的 Windows 與 Linux 執行測試。

## 結果與停止條件

三支腳本的 JSON 都有 `schema_version`、`status`、`scope` 與 `issues`。狀態與退出碼：

| status | exit code | 意義 |
|---|---|---|
| `PASS` | 0 | 該腳本宣告的範圍完成，沒有待處理項目 |
| `WARNING` | 1 | 分析完成但有差異，或 upload 身分尚未核對，需要審查 |
| `INCOMPLETE` | 2 | 缺資料、配對不唯一、部分分析或有不支援的項目，不能宣稱通過 |
| `ERROR` | 2 | 輸入、解析或執行錯誤，不能宣稱通過 |

其他 agent 必須同時檢查退出碼與當次 JSON；不能把「有報告／有 PNG／沒有橘框」解讀為 PASS。下游不接受無狀態的舊報告或上游非 PASS 為完整驗證；仍可產生診斷圖，但結果不會是 PASS。CLI 參數錯誤、無法寫入輸出或拒絕重用輸出目錄時可能沒有新 JSON，退出碼 2 仍代表失敗，不能使用舊報告代替。

`render_compare` 的 PASS 只表示輸入涵蓋與 rendering 完成，還要做逐層 pixel 比對。`pixel_compare` 有任何像素差異都回報 WARNING（容差與區域大小只控制顯示與分類，不能掩蓋差異）。`check_inner_removals` 的 PASS 只適用於所選圖層的去銅啟發式分析；沒有內層時不應拿空結果當通過。這些 PASS 都不是網表、製造公差、實板驗證或投產批准。

每次 rendering 使用全新或空的 `--out` 目錄，且放在來源資料夾之外，避免新舊 PNG／JSON 混用。錯誤報告只保留 exception 類型；詳細 console 訊息與相對檔名仍可能含私有資訊，公開前需自行檢查。

## 三個腳本

| 步驟 | 腳本 | 輸入 | 輸出 |
|---|---|---|---|
| 1 | `render_compare.py` | 原始 Gerber＋鑽孔（資料夾或 zip）、工廠生產稿（資料夾或 zip） | `layer-summary.json`、`<層>-orig.png`、`<層>-cam.png`、`panel-<檔名>.png` |
| 2 | `pixel_compare.py` | 步驟 1 的資料夾 | `<層>-diff.png`、`<層>-comparison.png`、`pixel-summary.json` |
| 3 | `check_inner_removals.py` | 步驟 1 的資料夾，可加 `holes.json` | `<層>-inner-check.png`、`inner-check.json` |

**render_compare.py**
- 依檔名配對圖層。原始端認 KiCad 命名（`*-F_Cu.*`、`*.gtl` 等）；工廠端認 JLCPCB 的無副檔名檔案（`tl bl l2 l3 ts bs to bo ko drl`）與一般副檔名。所有別名的候選一起檢查，只有唯一配對才使用；不再取第一個。`--pair 標籤=原始樣式,工廠樣式` 可覆寫，樣式含 `/` 時比對完整相對路徑，否則比對 basename。
- 必須有頂銅、底銅與外形；其他圖層只要任一端有檔案就需要配對。原始 CAM 有未配對的檔案也視為 INCOMPLETE。鑽孔樣式全部合併（包含 PTH／NPTH），同 basename 的多份 drill 不會自行選擇。非標準板型可用 `--only-pairs` 做診斷，但不能得到完整 PASS。
- 生產稿缺錫膏層等情況可用 `--omit-layer F_Paste=另行審查鋼網` 記錄原因；排除的圖層仍使結果為 INCOMPLETE，必須另有審查證據，不能拿剩餘圖層的成功代替。
- 找出原始→工廠座標的轉換：`--rotate`（逆時針度數，繞原點，先套用）加平移。平移可以自己給（`--offset 23 17`），或用 `--offset auto` 由鑽孔位置估算。
- 把原始板框（Edge_Cuts 中心線）轉進工廠座標當比較視窗，兩邊在同一視窗、同一解析度（預設 40 px/mm）光柵化。
- 鑽孔一對一配對，列出移動超過 `--moved-tol`（預設 0.005 mm）的孔、工廠缺少的孔、板內多出的孔、板外的孔（通常是工藝邊定位孔），以及原始孔徑→工廠孔徑對照（可看出補償）。
- 每個工廠 Gerber 另外輸出整個工藝框的預覽圖，用來認工藝邊、V-cut、孔處理標記。
- `--check-upload` 給工廠留存的「原送件副本」，依完整相對路徑比對每個成員檔的 SHA-256。不同目錄的同名檔不會互相覆蓋；缺檔、多檔、內容不同都回報 INCOMPLETE。工廠重新包裝了目錄時，先在新的工作副本確認並整理對應根目錄，不會自動猜 basename。未提供時 `upload_check.status=NOT_RUN`，整體至少 WARNING。
- slots 目前只計數、不比較幾何，因此有 slots 時 INCOMPLETE。parser warnings、空 artwork、缺／空 drill、缺外形、手動縮限視窗都不能取得完整 PASS。孔位、孔徑差異回報 WARNING；等距 drill 候選不選配，回報 INCOMPLETE。

**pixel_compare.py**
- 灰＝兩邊都有，紅＝只在工廠稿（新增），藍＝只在原始檔（移除）。超過容差的變動用橘框標出。
- `pixel-summary.json` 列出每層新增／移除面積（全部與超過容差兩種），以及每個變動區域的中心，同時給工廠座標與原單板座標。寫信給工廠時用原單板座標。
- 「畫出來的部分」在銅層是銅，在阻焊層是開窗，在絲印層是油墨。

**check_inner_removals.py**
- 對每個孔，在原始圖上從孔心往外填滿相連的銅。填不出 `--max-pad-mm` 方框、且只含一個孔的，視為該層未使用的孤立焊盤；其他視為有連接。
- 工廠移除的銅只有落在孤立焊盤內才算預期的處理（內層刪除非功能焊盤）。其他地方被移除、或有連接的焊盤中心銅不見，都列為可疑。
- 用 `--holes` 帶入網路名稱時，可加 `--plane-nets GND`，列出平面網路上失去中心銅的孔。
- 自訂 `--holes` 必須與步驟 1 的原始 drill 座標在 0.000001 mm 內唯一、一對一且完整對應。缺孔、多孔、重複或座標不符會回報 INCOMPLETE，並用原始孔位做診斷，不採信未核對的 net 標籤。`custom_holes_verified` 記錄核對結果。
- 兩張 PNG 除了尺寸互相一致，也必須完整涵蓋 `window_mm × ppmm` 的宣告範圍；同樣被裁切的兩張圖不能通過。

## 用法

```
python render_compare.py --original release/gerbers.zip --factory factory/production.zip --offset auto --out out
python pixel_compare.py --renders out
python check_inner_removals.py --renders out
```

常用選項：

| 選項 | 用途 |
|---|---|
| `--offset auto` / `--offset DX DY` | 平移量（mm）。auto 有多個候選位置時停止並回報 ERROR；請逐一用 `--offset` 指定 |
| `--rotate 90` | 工廠把板子轉了方向時使用，逆時針度數 |
| `--pair In1_Cu=*-In1_Cu.*,l2` | 新增或覆寫圖層配對；鋼網檔另外提供時也用它比錫膏層 |
| `--margin 0.5` | 視窗往外多看 0.5 mm，用於板邊附近的改動 |
| `--ppmm 80` | 提高解析度（記憶體與時間約按平方增加） |
| `--check-upload 原送件副本.zip` | 比對工廠留存的原送件與你的固定包 |

先拿同一份 Gerber 自我比對，確認環境正常（預期：偏移 (0, 0)、所有孔配對且誤差 0、每層差異都是 0）：

```
python render_compare.py --original gerbers.zip --factory gerbers.zip --check-upload gerbers.zip --out selftest
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
- 圖層配對靠檔名。對不上的層會記在 `layer-summary.json` 的 `issues` 並回報 INCOMPLETE，必須補足後重跑。只有兩邊都空的非必要圖層（例如未使用的底面錫膏）可以完成配對；必要的銅層與外形不能是空的。
- 解析依賴 gerbonara；解析警告數量記在 `layer-summary.json`。省略參數的圓弧等格式問題可能讓絲印有小差異，先排除解析問題再當成工廠改動。
- 外形層的線寬常與原始不同（工廠繪圖線較粗），外形差異以板尺寸和 V-cut 標註判讀，不看像素面積。
- 不解讀 ODB++、V-cut 語意、孔處理標記（如 `sk`）或拼板工序。這些要看圖面標註並問工程。
- 不檢查 PCBA 貼裝；貼裝座標與極性依流程文件人工核對。

## 隱私

輸出的 JSON 會記錄工廠檔案的成員名稱與雜湊，檔名可能含訂單編號；PNG 是工廠的生產資料。輸出留在私有目錄，不要提交到公開 repository。
