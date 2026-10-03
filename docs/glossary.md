# 術語表

這個 repo 常出現的名詞。依流程順序排列：設計、製造檔、板廠與下單。英文縮寫保留原樣，因為 KiCad 與 JLC 的介面都用英文。

## 設計

| 名詞 | 意思 |
|---|---|
| 原理圖（schematic） | 畫「哪些零件、怎麼連」的圖，不管實際位置。KiCad 檔案 `.kicad_sch` |
| PCB 佈局（layout） | 把零件擺到板子上、畫出銅線。KiCad 檔案 `.kicad_pcb` |
| symbol | 零件在原理圖上的符號 |
| footprint | 零件在 PCB 上的焊盤圖形。尺寸必須和實際買的料一致 |
| net／網路 | 電氣上連在一起的一組接腳，例如 `GND`、`3V3` |
| netlist | 所有網路的清單；修改前後比對它，可以看出連線有沒有被改到 |
| ERC | Electrical Rules Check，檢查原理圖的連線規則（例如輸出接輸出、腳位沒接） |
| DRC | Design Rules Check，檢查 PCB 的線寬、間距、未連線等規則 |
| 去耦電容（decoupling） | 放在 IC 電源腳旁邊的小電容，穩定電源 |
| via | 連接不同銅層的小孔 |
| 環寬（annular ring） | 孔周圍一圈銅的寬度 |
| 鋪銅（zone／pour） | 大面積的銅，通常接 GND |
| 板框（Edge.Cuts） | 板子外形的那一層 |
| 疊構（stackup） | 多層板每一層的材料與厚度 |
| DNP | Do Not Populate，畫在設計裡但不貼裝的零件 |
| 測試點（test point） | 留給量測用的焊盤 |

## 製造檔

| 名詞 | 意思 |
|---|---|
| Gerber | 板廠用的製造檔格式，每一層一個檔案，通常打包成 zip |
| 鑽孔檔（drill、Excellon） | 記錄每個孔的位置與孔徑 |
| PTH／NPTH | 孔壁有鍍銅（可導電）／沒有鍍銅（例如安裝孔） |
| 阻焊（solder mask） | 板子表面的綠漆（或其他顏色），防止焊錫流到不該去的地方 |
| 絲印（silkscreen） | 印在板上的文字與標記 |
| 錫膏層（paste）／鋼網（stencil） | 貼裝時刷錫膏用的開孔圖形 |
| BOM | Bill of Materials，零件清單：數值、位號、封裝、料號 |
| CPL | Component Placement List，每顆零件的座標、旋轉、面別。也叫 pick-and-place 或 position file |
| 位號（designator、reference） | 零件編號，例如 R1、C3、U1 |
| pin 1 | 零件的第一腳，用來判斷方向 |

## 板廠與下單

| 名詞 | 意思 |
|---|---|
| PCB／PCBA | 空板／貼好零件的板子（Assembly） |
| SMT／THT | 表面貼裝元件／直插元件 |
| LCSC 料號、C-code | JLC 與 LCSC 共用的零件編號，例如 `C14663` |
| MPN | Manufacturer Part Number，原廠料號 |
| Basic／Extended 料 | Basic 料長期裝在貼片機上；Extended 料需要換料，每種另收費用。Preferred Extended 在 Economic 組裝可免換料費（2026-10 觀察，以 JLC 網站為準） |
| Economic／Standard 組裝 | JLC 的兩種組裝服務等級，差在可貼的面、最小元件與尺寸限制，見 [jlc-ordering.md](workflow/jlc-ordering.md) |
| DFM | Design for Manufacturing，板廠檢查設計能不能做 |
| 生產稿（production file） | 工廠依你的檔案調整後、準備投產的版本，需要你確認 |
| 工藝邊（rails） | 加在板子外圍、讓機器夾持的邊條，貼裝後可拆 |
| 拼板（panel） | 多片板子排在一起生產 |
| V-cut | 拼板之間的 V 形切槽，方便折斷分板 |
| fiducial／定位點 | 讓貼片機對位的圓形銅點 |
| 表面處理 | 焊盤表面的處理方式：HASL（噴錫，便宜但不平）、ENIG（沉金，平整、較貴）、OSP（有機保護膜，便宜、拆封後要盡快焊） |

## 這個 repo 的用語

| 名詞 | 意思 |
|---|---|
| 發行包（release package） | 交給工廠的那一份固定檔案，之後不再修改，見 [release-package.md](workflow/release-package.md) |
| WORKLOG | 按時間記錄誰做了什麼、停在哪裡的工作紀錄 |
| 寫入者（writer） | 同一時間唯一可以修改設計檔的人或 agent |
| PASS／WARNING／INCOMPLETE／ERROR | 本 repo 腳本的結果狀態。只有 PASS 代表該腳本的檢查範圍全部通過；其他都需要處理或審查 |
