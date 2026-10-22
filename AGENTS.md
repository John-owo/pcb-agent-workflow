# pcb-agent-workflow：agent 工作規則

這個 repo 收錄一套 PCB 工作流程：用 Claude Code 或 Codex 搭配 KiCad 10 設計，交 JLCPCB 製造。內容包括流程文件、專案範本、skill、輔助腳本，以及一份實際下單過的範例設計。

Claude Code 透過 `CLAUDE.md` 匯入本檔；Codex 直接讀本檔。兩邊的規則只寫在這裡。

## 目錄

| 路徑 | 內容 |
|---|---|
| `docs/` | 新手入門、術語表、第一塊板檢查清單 |
| `docs/workflow/` | 流程文件：協作、KiCad 工具、發行包、JLC 下單（生產稿比對已併入 `skills/jlc-production-review/`） |
| `templates/` | 給新 PCB 專案複製使用的 `AGENTS.md`、`CLAUDE.md`、`WORKLOG.md`、`README.md`、`kicad-project.gitignore` |
| `.claude-plugin/marketplace.json` | Claude Code 與 Codex 共用的 plugin marketplace，每個 skill 一個 plugin entry |
| `plugins/` | 不屬於 skill 的 plugin，目前只有選用的 `jlc-send-guard` hook |
| `skills/` | Claude Code 與 Codex 共用的 skill，每個資料夾一個 `SKILL.md`；skill 用到的腳本放在該 skill 的 `scripts/`，跟著 skill 一起安裝 |
| `scripts/` | 不屬於單一 skill 的流程工具（發行包、Konnect 呼叫器），以及本 repo 的隱私掃描與 skill 檢查；各自在檔頭說明用法 |
| `examples/` | 固定發行包形式的範例設計，以及旁邊的 `*-tests/` 實測紀錄 |
| `CONTEXT.md` | 這套流程自己定義的用詞（給 agent 統一用語）；一般術語見 `docs/glossary.md` |
| `docs/agents/` | 工程類 skill 讀取的設定：issue tracker、triage 標籤、domain docs |

## 修改規則

- **不放個人資料。** 姓名、email、電話、地址、訂單號、購物車號、客戶代碼、本機絕對路徑、Windows 使用者名稱都不能出現。人員一律寫角色，例如「線上客服」「PCB 工程」。新增或修改內容後，提交前用規則檔掃一次（CI 也會跑；它會解開 zip 一起掃）：

  ```bash
  python -I scripts/check_privacy.py
  ```

  結果要是 `CLEAN`。環境變數名稱 `%LOCALAPPDATA%` 已列為允許，不算命中。新加的測試資料不要直接寫出會命中的字串，用拼接組出來（見 `tests/test_repo_checks.py`）。另外對照自己的姓名、帳號、信箱、客戶代碼再搜一次；掃描結果列出的圖片和 PDF 要打開來看。
- **不放截圖。** 截圖幾乎都含帳號資訊。需要圖示時，用重新繪製的示意圖或板圖。
- **不放原廠 datasheet。** 放原廠連結。第三方工具與 skill 寫來源、版本與授權，不附上本體。
- **範例設計包是固定發行包。** 不要用工具重新生成、重新填銅或另存檔案，也不要在裡面新增檔案。要修正就另開新版本資料夾，並在 README 說明差異。換行字元不轉換的設定見 `.gitattributes`。
  - 例外：範例的 `README.md` 是公開時重寫的說明，不是發行檔，可以更新（例如加上實測紀錄的連結、更正說明文字）。
  - 實板到貨後的**實測紀錄**與勘誤，放在範例包旁邊的 `examples/<範例>-tests/`，不寫進範例包的 `verification/`。`verification/` 只保存發行時的驗證。用詞見 `CONTEXT.md`。
- **時效性資訊要標快照日期。** JLC 的期限、價格、料庫狀態都會變，寫成「YYYY-MM 觀察」，並提醒讀者以當下的網站和信件為準。
- **skill 格式。** `SKILL.md` 的 frontmatter 要有 `name`（與資料夾同名）和 `description`（1024 字元內），description 同時寫中文與英文觸發詞。Codex 用的介面資訊放在 `agents/openai.yaml`。參考資料放 `references/`、腳本放 `scripts/`，從 `SKILL.md` 用相對路徑連過去；不要用只有某個 agent 會展開的變數。只在特定情境才需要的長段落移到 `references/`。
- **plugin 與版本。** 新增 skill 時，在 `.claude-plugin/marketplace.json` 加一個 `source` 為 `./`、`skills` 只列該 skill 的 entry。改了 skill 或腳本，就升該 entry 的 `version`（有 `plugin.json` 的 plugin 兩邊一起改），已安裝的使用者才會收到更新。改完用 `claude plugin validate .` 檢查。
- **工具搭配。** skill 提到 MCP 或外部工具時，只點名實際驗證過的工具與版本，其他寫類別並註明未驗證；同時寫出沒有該工具時的退路。原則是 MCP 看狀態與操作，腳本與 `kicad-cli` 判定。
- **語言。** 文件以繁體中文為主；寄給 JLC 的訊息範本用英文。

## 驗證

- 改了腳本：至少跑過 `--help`；能用範例資料測的就實際測一次。新腳本要附 `tests/` 測試，並加進 CI 的 `--help` 檢查。
- 改了範例設計包：用 KiCad CLI 在工作副本上重跑 ERC／DRC，結果寫進該版本的 `verification/`。
- 改了 skill：讀一遍 `SKILL.md`，確認硬規則裡要使用者同意的動作沒有被放寬；跑 `python -I scripts/check_skills.py`（也檢查全 repo 的 Markdown 相對連結）。

## Agent skills

### Issue tracker

Issues 記在本 repo 的 GitHub Issues，用 `gh` CLI 操作。See `docs/agents/issue-tracker.md`.

### Triage labels

沿用預設五個標籤：`needs-triage`、`needs-info`、`ready-for-agent`、`ready-for-human`、`wontfix`。See `docs/agents/triage-labels.md`.

### Domain docs

Single-context：根目錄一份 `CONTEXT.md`，決策記在 `docs/adr/`，需要時才建立。See `docs/agents/domain.md`.
