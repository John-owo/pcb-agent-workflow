# 固定發行包

製造檔交出去之後，板廠的問題、客服往返、補費都會指向「當時交出去的那一份」。所以送廠的版本要做成固定發行包：內容不再改，進度另外記。

## 固定內容與動態進度分開

| 類型 | 放哪裡 | 會不會再改 |
|---|---|---|
| 發行包：原生設計、元件庫、製造檔、驗證結果 | `releases/<版本>/` 或專案約定的固定位置 | 不改。要修正就開新版本 |
| 訂單、審稿、客服進度 | 發行包外的報告檔，例如 `reports/<訂單>-<日期>/` | 持續更新 |
| 目前該用哪一版 | 根目錄 README 的入口表 | 基準改變時更新 |

發行包內的 README 若寫了報價或交期，那只是發行當天的快照。

## 發行包要有什麼

```
<board>-<rev>/
├── <board>.kicad_pro / .kicad_sch / .kicad_pcb / .kicad_dru
├── fp-lib-table、sym-lib-table      # 用 ${KIPRJMOD} 相對路徑
├── footprints/、symbols/            # 這個版本用到的元件庫，成套保留
├── manufacturing/                   # Gerber＋鑽孔 zip、BOM、CPL、裝配圖、原理圖 PDF
├── verification/                    # ERC、DRC、release-checks.json、審查紀錄
└── README.md                        # 用哪些檔案製造、驗證過什麼、沒驗證什麼
```

- **元件庫用相對路徑。** 整個資料夾搬到別台電腦也能開。
- **不放** `.kicad_prl`（個人 UI 狀態）、自動備份、原廠 datasheet。
- 製造檔要**成套**使用：同一版的 Gerber、鑽孔、BOM、CPL、裝配圖。

## 雜湊清單與封裝

[scripts/package_release.py](../../scripts/package_release.py) 做四件事：

1. 對發行包內每個檔案算 SHA-256，寫成 `SHA256-files.json`。
2. 把整個資料夾和清單打包成 zip。
3. 重新打開 zip，逐一比對每個檔案的雜湊。
4. 寫出 zip 本身的 `.sha256.txt`。

```bash
python scripts/package_release.py --src releases/my-board-revC --out dist
```

雜湊清單用來確認「這就是當時那一份」，不能拿來還原。要能還原，就保留完整的 zip 或 commit。

`SHA256-files.json` 識別相對路徑與檔案內容；相同內容重新封裝時，清單應相同。zip 的 `.sha256.txt` 則只識別**這次產生的封裝檔**，不保證 deterministic rebuild（相同內容重建會得到逐位元相同的 zip）：ZIP 會保留來源檔的時間、權限等 metadata，產生的清單也有當次時間，Python／壓縮函式庫版本也可能影響封裝。要驗證收到的發行包，使用該包隨附的 ZIP 雜湊；要跨次重建比較內容，逐項比較檔案清單。不要把重建 ZIP 的雜湊不同直接解讀為製造檔改變。

腳本的 `all_entries_verified: true` 只表示封裝後的內容雜湊檢查完成；它不表示 ERC／DRC、CAM／Gerber 完整性、板廠接受或實板驗證通過。

## release-checks.json

把發行前的檢查寫成機器可讀的檔案，之後比對、審查都方便。建議的欄位：

```json
{
  "revision": "C",
  "checked_at": "2026-09-21T18:00:00+08:00",
  "design_file_checks_pass": true,
  "order_readiness": "READY | BLOCKED_<原因>",
  "hardware_validation": "NOT_RUN",
  "blockers": ["還沒解決、會擋住下單的事，用角色描述，不寫人名"],
  "checks": [
    { "check": "ERC no violations or ignored checks", "pass": true, "detail": null },
    { "check": "DRC: no violations, unconnected items, parity issues", "pass": true, "detail": null },
    { "check": "R5: schematic MPN, C-code, footprint and BOM agree", "pass": true, "detail": null },
    { "check": "Gerber zip contains In1_Cu", "pass": true, "detail": null }
  ]
}
```

- `hardware_validation` 在實板測過之前一律是 `NOT_RUN`。
- 庫存、耗損這類會變的事，寫進 `detail` 並標日期，不要算成通過。

## 版本資料夾命名

過程中常會留下好幾份相似的副本。名字要能看出用途：

| 名稱 | 意思 |
|---|---|
| `before-complete.zip` | 修改前的完整備份 |
| `candidate/` | 修改中的候選版本 |
| `review-snapshot.zip`、`review-r1-fixed.zip` | 交給審查的固定版本，以及第一輪修正後的版本 |
| `<board>-<rev>-<YYYYMMDD>.zip` | 正式發行包 |

`candidate`、`review`、`fixtures` 裡也有同名的 PCB，但它們不是最新版，也不能只因檔名重複就刪除。目前該用哪一版，以 README 入口表為準。
