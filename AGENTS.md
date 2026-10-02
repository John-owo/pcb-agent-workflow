# pcb-agent-workflow：agent 工作規則

這個 repo 收錄一套 PCB 工作流程：用 Claude Code 或 Codex 搭配 KiCad 10 設計，交 JLCPCB 製造。內容包括流程文件、專案範本、skill、輔助腳本，以及一份實際下單過的範例設計。

Claude Code 透過 `CLAUDE.md` 匯入本檔；Codex 直接讀本檔。兩邊的規則只寫在這裡。

## 目錄

| 路徑 | 內容 |
|---|---|
| `docs/workflow/` | 流程文件：協作、KiCad 工具、發行包、JLC 下單、生產稿比對 |
| `templates/` | 給新 PCB 專案複製使用的 `AGENTS.md`、`CLAUDE.md`、`WORKLOG.md`、`README.md` |
| `skills/` | Claude Code 與 Codex 共用的 skill，每個資料夾一個 `SKILL.md` |
| `scripts/` | 輔助腳本；各自在檔頭或 README 說明用法 |
| `examples/` | 固定版本的範例設計包 |
| `docs/agents/` | 工程類 skill 讀取的設定：issue tracker、triage 標籤、domain docs |

## 修改規則

- **不放個人資料。** 姓名、email、電話、地址、訂單號、購物車號、客戶代碼、本機絕對路徑、Windows 使用者名稱都不能出現。人員一律寫角色，例如「線上客服」「PCB 工程」。新增或修改內容後，提交前用 `rg` 掃一次。
- **不放截圖。** 截圖幾乎都含帳號資訊。需要圖示時，用重新繪製的示意圖或板圖。
- **不放原廠 datasheet。** 放原廠連結。第三方工具與 skill 寫來源、版本與授權，不附上本體。
- **範例設計包是固定版本。** 不要用工具重新生成、重新填銅或另存檔案。要修正就另開新版本資料夾，並在 README 說明差異。換行字元不轉換的設定見 `.gitattributes`。
- **時效性資訊要標快照日期。** JLC 的期限、價格、料庫狀態都會變，寫成「YYYY-MM 觀察」，並提醒讀者以當下的網站和信件為準。
- **skill 格式。** `SKILL.md` 的 frontmatter 要有 `name` 和 `description`，description 同時寫中文與英文觸發詞。Codex 用的介面資訊放在 `agents/openai.yaml`。參考資料放 `references/`，從 `SKILL.md` 連過去。
- **語言。** 文件以繁體中文為主；寄給 JLC 的訊息範本用英文。

## 驗證

- 改了腳本：至少跑過 `--help`；能用範例資料測的就實際測一次。
- 改了範例設計包：用 KiCad CLI 在工作副本上重跑 ERC／DRC，結果寫進該版本的 `verification/`。
- 改了 skill：讀一遍 `SKILL.md`，確認硬規則裡要使用者同意的動作沒有被放寬。

## Agent skills

### Issue tracker

Issues 記在本 repo 的 GitHub Issues，用 `gh` CLI 操作。See `docs/agents/issue-tracker.md`.

### Triage labels

沿用預設五個標籤：`needs-triage`、`needs-info`、`ready-for-agent`、`ready-for-human`、`wontfix`。See `docs/agents/triage-labels.md`.

### Domain docs

Single-context：根目錄一份 `CONTEXT.md`，決策記在 `docs/adr/`，需要時才建立。See `docs/agents/domain.md`.
