# 驗證與維護

## 檢查能證明什麼

| 層級 | 證據 | 不代表 |
| --- | --- | --- |
| 桌面 fixtures | parser、假 ADB、暫存 HOME/PREFIX、渲染與可重複性 | Android 執行或真正 USB 配對 |
| Asset 分析 | 固定版本、大小／hash、架構與 loader metadata | PTY、網路、認證或 sandbox 行為 |
| 裝置 smoke | Android/Termux 版本與實際指令結果 | 所有廠商或背景政策 |
| Agent session | 認證與保留預期防護的代表性工具操作 | 未來版本或任意負載 |

CI 在 macOS 與 Ubuntu 執行 fixtures，不需要連接手機、真實配對憑證、provider
key 或 maintainer 正在使用的 chezmoi source。版本字串不等於 runtime 支援。

## 桌面檢查

維護檢查需要電腦已安裝 just、uv、ShellCheck 與 chezmoi。
在 maintainer checkout 內：

```sh
just check
```

各項檢查可分別執行：

```sh
bash scripts/lint.sh
uv run --no-project --python 3.12 python -m unittest discover -s tests -v
uv run --no-project --with 'mkdocs<2' --with mkdocs-material --with mkdocs-static-i18n mkdocs build --strict
bash scripts/todo-kanban.sh --validate-only TODO.md
```

ShellCheck 檢查受維護 scripts。測試使用暫存路徑與明確 fixture-only 環境標記。
公開 commit 前與 CI 都執行 secret checks。配對 keys、裝置識別資料、known-hosts
與 runtime state 不可放進 repository。

## 明確的原生 probes

選用並安裝工具後，只在原生 Termux 內執行：

```sh
bash scripts/tools.sh probe herdr
bash scripts/tools.sh probe codex
```

Herdr probe 建立私有暫存設定、獨立 headless server 與明確的 workspace，檢查
PTY、指令輸入／輸出與分割，結束時只清理自己的 session。互動式 SSH rendering、resize 與 reconnect
仍需手動驗收。

Codex probe 使用獨立 `CODEX_HOME`，在原本的 read-only sandbox 執行無害指令，
並確認寫入被拒絕，不加入 bypass flags。sandbox 無法初始化就是該項失敗，
不代表可以放寬防護。認證、DNS/TLS 與互動行為仍需另外驗證。

## 裝置驗收

記錄日期、Android 版本/API、架構、Termux app 版本／來源、相關工具版本，
以及在原生或 PRoot 執行。serial 與帳號資料保持私有。

1. 完成 setup、重新連線，再重跑 setup。無關 shell 內容、SSH keys 與 Boot
   scripts 必須保留。
2. 在本機 Termux tab 與新的 SSH login，使用 `$HOME` 下的 scratch 目錄驗證
   Bash、Starship、Git、Vim 與 tmux。
3. 連續套用設定兩次，第二次必須穩定，兩次都不得安裝或升級套件。
4. 測試明確的完整套件同步與中斷重試；失敗清楚顯示，正常執行檔不被覆蓋。
5. 依模式測試 LAN 與僅 loopback SSH、錯誤／未信任 keys、其他程序已占用
   port，以及移除 USB 後重新連線。
6. 開啟 Termux:Boot 一次，重開機確認受管理服務。關閉螢幕後的行為要另外
   測試，並記錄電池設定。
7. 完成已選的 [agent 檢查](tools.md)，包含原本的 sandbox 行為。無法執行的
   項目應標示 unverified，而非 passed。

## 更新固定下載檔

一起檢查上游 metadata 與實際 artifact。版本、精確 URL、SHA-256 與預期大小
必須在同一變更更新，並核對架構與 archive members。APK 更新保留 F-Droid
簽章來源。不要因下載失敗就接受不同 hash，也不要 commit APK 或執行檔。
選用工具更新後需重新進行裝置 probe；檔名有 `musl` 不代表 static linkage。

## 專案記憶

`TODO.md` 是未來工作索引，`backlog/` 保存能接續工作的研究，`pitfalls/` 索引
已調查症狀。這些資料都在 chezmoi source root `home/` 外，不會部署。

repo 內的維護 scripts 來自 `project-knowledge-harness`：

```sh
bash scripts/add-todo.sh --priority P3 --effort S --title 'Example' --description 'A concrete future improvement'
bash scripts/todo-kanban.sh --validate-only TODO.md
```

需要研究筆記時加上 `--backlog`，其模板位於 `backlog/.backlog-doc.md.template`。
新增使用者文件需維持 English/zh-TW 成對，並更新 `mkdocs.yml` navigation 與翻譯。

## Shell 與 uv 後續驗證 — 2026-09-13

ARM64 Android 15 平板已選用原生 zsh 5.9.2，保存值與 Termux 實際 shell override
一致；新的 Termux／SSH login 使用 zsh，保留既有 sessions。裝置上的舊版 `chsh`
需要相對名稱，selector 使用新舊版本皆支援的寫法。

- 每種 shell／目錄交錯量測 30 次暖啟動，通過效能門檻。使用相同受管理 helpers
  時，zsh 中位數 186–190 ms，Bash 116–119 ms；zsh P95 204–208 ms，冷快取
  692–694 ms。[方法與重現方式](shell.md)見 Shell 文件。
- 新 SSH session 載入 zsh、Starship、語法上色與 helpers；輸入 `dev sta` 再按
  Tab，可看到 start/stats/status 選項，dev 與 uv 補全函式也正常註冊。
- 使用裝置設定建立獨立 Herdr server，通過 zsh pane、helpers、uv、dev 補全
  與 split，之後移除測試狀態。Herdr 曾在 seed 加入 onboarding 欄位，因此這次
  明確備份後只修改 default_shell，保留 onboarding。
- uv 0.12.13（`aarch64-linux-android`）成功建立 Python 3.14.6 venv、從 PyPI
  安裝 `packaging==25.0`，也通過 `uv run --no-project --with`。預設使用系統
  Python 與 copy 模式；後续本機設定仍會保留。
- 連續兩次 chezmoi apply 後沒有受管理檔案差異。管理與 Boot 腳本仍由 Bash 執行。

本機完整 suite 通過 110 項測試；CI 後來發現舊 Bash 的 EXIT trap 區域變數
生命週期差異，以及 fake OMZ fixture 少了實際框架使用的 `compinit -i`，均已
修正，沒有關閉補全安全檢查。最終版本的 macOS／Ubuntu 結果見
[Checks workflow](https://github.com/daviddwlee84/dotfiles-Termux/actions/workflows/check.yml)。
重開機／背景行為與全新 ADB pairing 仍是獨立驗證項目；這次重用既有 USB SSH 配對。

## 原生 SSH setup 修正 — 2026-09-13

ARM64 Android 15 裝置使用原生 Termux Go 1.27.1 與 Clang：

- 原本 v0.2.35 的 SSH wizard 拒絕 Android 系統管理的 `/data`；discovery cache
  也因 app sandbox 禁止從 `/` 開啟目錄及透過 hard link 發布檔案而失敗。
- v0.2.36 修正會驗證 Termux 私有家目錄邊界、保留繼承的 SELinux／加密 metadata，
  並用 `RENAME_NOREPLACE` 發布新檔案。沒有修改 Android 系統權限或安全政策。
- 八個原生檔案系統／SSH domain test packages 與 SSH TUI adapter tests 均通過，
  包含原生金鑰生成、cache 保存與標籤不符拒絕。Android 不允許建立 hard-link
  攻擊 fixture 時會明確 skip；desktop 測試仍涵蓋那些案例。
- 實際 Termux dashboard 成功審閱並套用 configuration-only 連線：初始化 SSH
  config、建立 managed fragment 與 machine binding，通過原生有效設定驗證，
  回報 `SSH setup: ready`，並在清單顯示為 managed 連線。

正式發布後，實際執行 `dev upgrade --yes`，以有 checksum 的 3,687,265-byte
source archive 將已安裝的 v0.2.35 升級至 v0.2.36。已有依賴與 build cache 時，
下載及原生編譯共 **18.5 秒**。`dev --version` 與 `dev upgrade --check` 均確認
v0.2.36，並保留 v0.2.35 的私有復原副本。

這次驗證設定建立與原生檔案系統行為；實際連線尚未認證，也沒有向遠端主機
安裝金鑰。

## 原生 dev 升級至 v0.2.35 — 2026-09-13

ARM64 Android 15 裝置使用原生 Termux Go 1.27.1 與 Clang：

- 發布前，self-update unit tests 與實際精簡 source build 均通過；有快取的
  source build 耗時 15.9 秒，Git lookup 也通過。
- [dev-cli v0.2.35](https://github.com/daviddwlee84/dev-cli/releases/tag/v0.2.35)
  發布後，先讓隔離的開發版 binary 執行真正的 `dev upgrade`。它選用正式發布、
  大小為 3,676,371 bytes 的 source archive，驗證 SHA-256，以原生 Go/Clang
  及兩個 workers 編譯，確認候選版本後替換自身。下載、驗證與編譯在
  **已有依賴及 build cache 的情況下約 11 秒完成**。
- 驗證過的 v0.2.35 已安裝到 `~/.local/bin/dev`，並私有備份先前的原生 v0.2.33。
  Git repository 導航成功，實際 TUI 可在 PTY 下顯示、按 `q` 正常離開；
  `dev upgrade --check` 確認 v0.2.35 已是最新版。
- 裝置 checkout 以 fast-forward 更新到固定 v0.2.35 的安裝設定，之後移除
  暫時的測試 repository、binary 與狀態。

版本鎖更新通過 111 項 desktop fixtures、獨立 installer 測試、雙語 strict docs
與 secret checks；[macOS/Ubuntu CI](https://github.com/daviddwlee84/dotfiles-Termux/actions/runs/34751565943)
也已通過。完整 task/worktree lifecycle 與已登入的 agent 使用仍各自驗證。

## Herdr 與 dev-cli 後續驗證 — 2026-09-13

同一台 ARM64 Android 15 裝置的結果：

- Herdr 0.9.0 原本就已安裝；完整原生套件同步後，隔離的 PTY/run/read/split
  probe 再次通過。
- 完整套件同步及 `herdr,codex,dev` 選擇成功完成，保留 Pi 與完整 Codex package；
  沒有新增 Codex sandbox 通過的宣稱。連續兩次 chezmoi apply 後沒有受管理檔案差異。
- Linux dev-cli v0.2.33 artifact 雖通過啟動檢查，卻在查找 Git 時於
  `syscall.faccessat2` 崩潰。已改用原生 source build；詳見
  [失敗與遷移紀錄](https://github.com/daviddwlee84/dotfiles-Termux/blob/main/pitfalls/dev-sigsys-faccessat2.md)。
- source installer 使用 Termux Go 1.27.1/Clang 建置 Android 版 dev-cli v0.2.33，
  執行檔採用 `/system/bin/linker64`。在隔離 HOME 內通過含空白路徑的 Git repository
  導航、Markdown note 建立及 SQLite 全文搜尋，之後移除 probe 狀態。
- 新的互動 SSH login 正常載入 dev shell wrapper 與補全；實際 dev TUI 可開啟、
  切換到 REPOS、顯示 Termux checkout，再按 `q` 正常離開。此裝置已初始化自己的
  dev config，沒有複製電腦設定。

完整 task/worktree lifecycle、dev 對 Herdr 的操作、網路中斷恢復、重開機／背景
行為與已登入的 agent 使用仍是獨立的待驗證項目。

## 目前驗證紀錄 — 2026-09-09

已發布的基準證據：[GitHub Actions run 34298511347](https://github.com/daviddwlee84/dotfiles-Termux/actions/runs/34298511347)
在 `ad710fe` 通過，包含 71 項 fixtures（host 39、target 19、optional tools
13）、macOS/Ubuntu matrix、雙語 strict docs 與 gitleaks。先前本機驗證也通過
umbrella 的 13 項 orchestration tests、lint 與 harness validation。這些證據
對應其特定 revisions，不自動代表後續 commits；後續狀態請看
[Checks workflow runs](https://github.com/daviddwlee84/dotfiles-Termux/actions/workflows/check.yml)。

後續本機 `just check` 在 455 秒內執行 87 項 fixtures，最後有五項超過既有
時限：三項 Codex package 測試超過 30 秒、兩項 Herdr 測試超過 10 秒。
獨立 package 測試在 Python 3.12 與 3.14 都曾逾時，原因未確認，測試時限與
assertions 維持原樣。`38cbc3c` 的 macOS CI job 在 61 秒內通過全部 87 項，
Ubuntu 則停在已改寫為明確條件判斷的 ShellCheck 表達式。本機 lint、使用快取
的 strict docs 與 secret checks 通過；本機完整測試沒有記為通過。

四個固定 APK 的實際下載檔均通過大小／SHA-256 與 signer-certificate 檢查。
主機依賴 installer 已安裝 ADB 37.0.1。較早的 startup probes 曾逾時，之後完成
裝置授權後 ADB 已可正常通訊；先前逾時的原因沒有確認。

測試裝置為 **Xiaomi Pad 6S Pro 12.4**，**ARM64**，執行
**Android 15 / API 35 / HyperOS 2.0**。此處不保存 serial、Android user ID、
位址、keys 或私有 runtime state。

| 檢查 | 已確認結果 |
| --- | --- |
| APK 部署 | F-Droid／Termux 以相符 signer 完成安裝或更新；Termux:Boot 已安裝並開啟 |
| 首次指令傳送 | 自動輸入至已驗證的新 Termux shell 成功 |
| USB SSH 與接續 | 配對／嚴格 host-key pinning 成功；中斷 setup 透過已保存的 SSH 接續，無需重新輸入 |
| LAN SSH | 直接連線 port 8022，使用相同 pinned host identity 通過 |
| 完整 setup 重跑 | 在 `38cbc3c` 以 0 結束；重用 SSH、保留 apps、完整原生套件同步無變更、保留 Pi/Herdr，且完整 Codex package 無需下載即驗證成功 |
| 設定 | 連續兩次 chezmoi apply 後，排除 scripts 的 status 都為空；`sshd -t` 與受管理 SSH 設定一致性通過 |
| 一般 SSH login | Bash 與彩色 prompt 正常；`PROMPT_COMMAND=starship_precmd`、`ll='ls -al'`、`g='git'`；正常以 0 離開 |
| 健康檢查 | host 與 target doctor 均以 0 結束；下方獨立的 Codex sandbox 檢查仍失敗 |
| tmux | 原生獨立 PTY 輸入、分割兩個 panes 與 resize 通過 |
| Herdr 0.9.0 | 明確建立 workspace 的 headless run/read/split 通過；互動式 SSH TUI 接受輸入，Ctrl+b q detach/reattach 後 marker 保留，測試在同一條 SSH 連線內 |
| Pi 0.85.1 | 已安裝；未載入憑證的獨立 UI 正常顯示 `No models available` / `/login`；測試到期以 124 結束 |
| Codex 0.153.4 | 已安裝完整官方 package，包含 code-mode host、rg、bwrap、zsh 與 manifest；`--version` 通過，原本的 sandbox 如下方錯誤失敗 |
| Boot | app 已安裝並開啟一次；可執行 hook 通過 `bash -n`；未測試重開機／背景行為 |
| 裝置網路 | 起初 GitHub TLS EOF／timeout；使用者自行啟用 VPN 後，GitHub 與 `git ls-remote` 成功 |

Codex 的原始錯誤為：

```text
bwrap: Can't read /proc/sys/kernel/overflowuid: Permission denied
```

這證明正常 sandbox 啟動時的一次檔案讀取被拒絕，不能據此認定 user namespaces
已停用。測試沒有使用 sandbox bypass。

先前 hard-link 安裝失敗已改用 no-clobber rename 與明確的 skip 偵測處理；安裝
結果與 runtime 驗收分開。Pi 的 124 是預定的測試 timeout，不是 app crash 或
正常離開的證據，沒有執行 provider 登入或 model call。

P1 仍保留：實體／網路中斷恢復、Herdr 互動 resize、關螢幕／背景行為、真正
重開機後的 Boot，以及 agent 認證／模型／工具操作。Herdr 在同一 SSH 連線內
的 detach/reattach 不代表網路斷線後也能保留。VPN 是使用者自行選擇，程式沒有
修改全域網路設定，也沒有實作 offline bundle。

Repository：[github.com/daviddwlee84/dotfiles-Termux](https://github.com/daviddwlee84/dotfiles-Termux)。
