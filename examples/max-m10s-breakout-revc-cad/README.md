# MAX-M10S 轉接板 Rev C：外殼設計用 3D 檔

來源設計：[../max-m10s-breakout-revc/](../max-m10s-breakout-revc/README.md) 的 `MAX-M10S-Passive.kicad_pcb`（固定發行包，未修改）。用 [kicad-enclosure-step](../../skills/kicad-enclosure-step/SKILL.md) skill 產生，也當作那個 skill 的範例。這份檔案只用來設計外殼，不是製造檔。

![正面](preview-top.png)

## 檔案

| 檔案 | 內容 |
|---|---|
| `MAX-M10S-RevC.step` | 整板加 19 個零件。5 個測試焊盤沒有高度，不放模型 |
| `preview-top.png`、`preview-bottom.png` | 正面、背面算繪 |
| `enclosure-step.json` | 匯出設定：每種封裝用哪個模型 |
| `models/*.json` → `models/*.step` | 三個自畫模型的尺寸規格（含出處）與產生的 STEP |

重新產生（repo 根目錄執行，需要 KiCad 10 與 CadQuery）：

```bash
python skills/kicad-enclosure-step/scripts/simple_model.py examples/max-m10s-breakout-revc-cad/models/*.json
python skills/kicad-enclosure-step/scripts/export_step.py examples/max-m10s-breakout-revc-cad/enclosure-step.json --render examples/max-m10s-breakout-revc-cad/preview
python skills/kicad-enclosure-step/scripts/verify_placement.py examples/max-m10s-breakout-revc-cad/enclosure-step.json
```

## 座標

- 單位 mm。原點在板子左下角、板底面；+X 向右，+Y 向上，+Z 朝零件面。
- 板子 25.0 × 36.5 × 1.6 mm，佔 x 0–25、y 0–36.5、z 0–1.6。天線座 J1 在上緣（y 大的一側）。
- 整體外框：x 0–25、y 0–36.5、z −8.63 至 +4.10。

## 外殼要注意的地方

| 項目 | STEP 位置 | 說明 |
|---|---|---|
| 正面最高點 | U1 MAX-M10S，x 7.45–17.55、y 17.05–26.75 | 頂端 z 4.10（高出板面 2.5 mm，規格書典型值；最大 2.7） |
| 天線座 J1（I-PEX MHF I） | x 14.3–17.3、y 32.4–35.0 | 母座高 1.25 mm。插上 20670 系列插頭後最高 2.5 mm（z 約 4.1）；線材從插頭側面出去，外殼要留走線出口。被動天線與線材不在 STEP 裡 |
| 電源／PPS LED（D2、D3） | x 15.2–16.8、y 3.9–4.7（D2）與 1.6–2.4（D3） | 0603，高 1.1 mm。要看燈號就在這裡開窗或用導光 |
| 排針 J2、J3 | J2 x 2.3–4.9，J3 x 20.1–22.7，y 2.0–17.2 | 從板底插入：塑膠座在背面，針往下伸到 z −8.63；焊點端在正面凸出約 1.3 mm（到 z 2.92）。兩排中心距 17.78 mm，可以直接插麵包板 |
| 背面 | 只有排針 | 沒有其他零件 |
| 安裝孔 | 無 | 外殼要靠排針或夾住板邊固定 |

`verify_placement.py` 高度表（2026-10-22）：19 個零件全部通過。

## 模型來源

| 封裝 | 位號 | 來源 |
|---|---|---|
| C_0603、R_0603、LED_0603、SOT23、Header_1x06 | C1–C3、R1–R8、D2、D3、Q1、J2、J3 | KiCad 10 官方 3D 庫，以 `${KICAD10_3DMODEL_DIR}` 引用。這些封裝是官方庫改名、焊盤沒改（見 repo 的 NOTICE），位移都是 0 |
| MAX_M10S | U1 | 自畫：u-blox MAX-M10S data sheet（UBX-20035208 R08）Table 21，9.7 × 10.1 × 2.5 mm（典型值） |
| MHF_I | J1 | 自畫：I-PEX 20279-001E-03 圖面，本體 2.6 × 3.0 mm、高 1.25 mm |
| PESD3V3C1BSF | D1 | 自畫：Nexperia DSN0603-2（SOD962-2），0.6 × 0.3 × 0.3 mm |

自畫模型只畫外形包絡。外殼開孔與卡扣的關鍵尺寸，請以實物量測為準。

## 授權

- 自畫模型（`models/`）和本頁：依 repo 的 MIT。
- `MAX-M10S-RevC.step` 內含 KiCad 官方 3D 庫的幾何；依 KiCad 函式庫例外條款，用到這些模型的輸出可以自由使用。見 repo 的 NOTICE。
