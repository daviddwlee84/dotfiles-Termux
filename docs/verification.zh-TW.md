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

Herdr probe 建立私有暫存設定與獨立 headless server，檢查 PTY、指令輸入／輸出
與分割，結束時只清理自己的 session。互動式 SSH rendering、resize 與 reconnect
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

## 目前驗證紀錄 — 2026-09-09

macOS maintainer 主機的各測試套件共 65 項 fixture tests 通過（host 35、target
19、optional tools 11）；umbrella 的 13 項 orchestration tests 也通過。
Lint、harness validation 與 English/zh-TW strict MkDocs build 通過。
這些是桌面驗證結果，不是 Android runtime 測試。

四個固定 APK 的實際下載檔均通過大小／SHA-256 與 signer-certificate 檢查。
`host-deps.sh --install` 已安裝 ADB 37.0.1。實際執行 `adb devices -l` 時，
startup 在 120 秒後逾時；`adb version` 也停滯，probe 自己啟動的程序已終止。
原因尚未確認。因此裝置是否可用、Android 執行、USB SSH 配對與 Boot 行為仍然
未驗證；這不是「沒有連接裝置」的結論。

公開 repository 已建立：
[github.com/daviddwlee84/dotfiles-Termux](https://github.com/daviddwlee84/dotfiles-Termux)。
[GitHub Actions run 34262880520](https://github.com/daviddwlee84/dotfiles-Termux/actions/runs/34262880520) 已在程式 commit `c9cc7ce` 通過：macOS 與 Ubuntu 各執行全部 65 項 fixtures，雙語 strict docs 與獨立 gitleaks job 也通過。這些仍是桌面檢查，不代表 Android runtime 驗收。
