---
name: jlc-production-review
description: '審查 JLCPCB 付款後寄來的 PCB 生產稿（Confirm Production）與 PCBA 貼裝確認（Confirm Parts Placement）：把工廠 CAM 改過的 Gerber 對齊回你送出的固定製造包，逐層比對銅、孔、阻焊、絲印、外形，核對貼裝數量、位置、角度與極性，分類每個差異，寫出待工廠說明的清單；確認與寄信都等使用者決定。附比對腳本與 BOM／CPL 檢查。Use when reviewing a JLCPCB production file or parts placement confirmation, diffing factory CAM Gerbers against the original release, or checking BOM/CPL before upload. Triggers: "審生產稿", "比對生產稿", "貼裝確認", "工廠改了 Gerber", "BOM CPL 檢查", "review production file", "confirm parts placement", "CAM diff".'
---

# JLC 生產稿與貼裝確認審查

目標：在期限前，讓使用者拿到一份能據以決定的審查結果。agent 只做比對、分類和起草；確認、寄信、下載都等使用者。

## 硬規則

以下動作每一次都要使用者在聊天中明確同意：

- 從網站下載工廠檔案（或請使用者自己下載後給路徑）
- 按 Confirm Production、Confirm Parts Placement、Submit，或改動網站上的確認選項
- 接受工廠的改動、加費、補償或改期；要求工廠移動元件或修改 CAM
- 修改設計或固定製造包

確認頁的選項可能一打開就呈選取狀態，這不代表已提交，不要動它。結論只寫「未發現明確的錯版、漏孔或極性錯誤；以下 N 項待工廠說明」，不寫「可以投產」。

和工廠溝通（寄澄清信、催辦）交給 jlc-support skill；沒有安裝時，依本 skill 的 [references/procedure.md](references/procedure.md)「寫澄清給工廠」一節起草，寄出一樣等使用者同意。

## 流程

1. **算期限。** 收信當下把收信時間加上期限，換算成含時區的絕對時間，寫進 WORKLOG 並告訴使用者。PCBA 貼裝確認逾期會直接投產。有安裝 jlc-support 時用它的 `scripts/deadline.py`。
2. **鎖定基準。** 用實際送出的固定製造包，不用較新的設計。工廠 ZIP 存私有目錄並記 SHA-256。
3. **確認工廠拿到對的版本。** `render_compare.py --check-upload` 比對原送件副本（JLC 的 `YG`）與固定包。
4. **逐層比對。** 對工廠的 CAM 稿（`ok`）跑三支腳本，每次用新的私有輸出目錄，然後在 Gerber Viewer 目視複查。
5. **分類差異。** 常見 CAM 處理照樣記錄；可疑項目列成待問清單。分類表見 procedure.md 第 3 節。
6. **核對貼裝。** 數量、料號、位置（CPL 單板座標加同一平移量）、角度、pin 1 與極性。
7. **交付。** 審查報告、待問清單、澄清信草稿、剩餘期限，交使用者決定。

## 工具搭配

原則：MCP 負責看當下狀態，腳本負責判定。MCP 回覆「成功」不算驗收。

| 步驟 | MCP／工具 | 腳本（相對於本 skill 資料夾） | 通過條件 |
|---|---|---|---|
| 看確認頁、到期資訊 | 瀏覽器：Claude in Chrome（Claude Code）；ChatGPT browser extension（Codex 桌面版 `@Chrome`，Codex CLI 不支援）。只讀，不點選項、不下載 | — | 記下詳細狀態與核對時間 |
| 找確認信 | 信箱：Gmail connector（claude.ai 或 ChatGPT）。先確認連到訂單註冊帳號 | — | 收信時間與期限已記錄 |
| 版本核對、對齊、鑽孔比對 | — | `scripts/render_compare.py` | 看退出碼與 JSON `status` |
| 逐層像素比對 | — | `scripts/pixel_compare.py` | 每個 WARNING 都已分類 |
| 內層去銅 | — | `scripts/check_inner_removals.py`（可帶 `holes.json`） | 只刪了孤立焊盤 |
| 貼裝前後的 BOM／CPL | — | `scripts/check_bom_cpl.py` | PASS，或每個 WARNING 有原因 |

- 安裝相依：`python -m pip install -r scripts/requirements-cam.txt`（Python 3.12）。`check_bom_cpl.py` 只用標準庫。
- 退出碼 0 是 PASS、1 是 WARNING、2 是 INCOMPLETE 或 ERROR。INCOMPLETE／ERROR 不能寫成通過；有報告、有圖、沒有橘框，也都不代表 PASS。
- 沒有瀏覽器或信箱工具時，請使用者貼上確認信內容與頁面狀態，報告裡註明「狀態由使用者提供，未直接核對」。
- 腳本只看圖形，不懂網路；光柵比對不是網表證明。請工廠回覆網表比對結果。

## 停止條件

- 腳本 INCOMPLETE／ERROR：補資料或修正後重跑，不拿部分圖層的結果交差。
- 期限快到而使用者還沒決定：再提醒一次，不代為確認。
- 找到可疑差異：停在起草澄清信，等使用者決定是否寄出。

## 參考

- [references/procedure.md](references/procedure.md)：完整審查程序：圖層對照、座標轉換、差異分類表、貼裝核對、誰可以做什麼、記錄方式
- [references/cam-diff.md](references/cam-diff.md)：三支比對腳本的選項、結果狀態、限制、產生 `holes.json` 的方法
