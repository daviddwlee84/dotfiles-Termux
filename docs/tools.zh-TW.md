# 工具與相容性

基礎環境維持原生 Termux。以下套件與相容性資料於 **2026-09-09** 查核；
第一台 Android 裝置已有部分安裝／啟動結果；已完成與待驗證項目請見
[驗證紀錄](verification.md)。

| 工具 | 安裝方式 | 此 repo 的支援層級 |
| --- | --- | --- |
| chezmoi、Bash、Starship、Git、Vim、tmux、Python 與編譯工具 | 官方 Termux 套件 | 原生基礎；仍需裝置驗收 |
| Node.js LTS 與 npm | 官方 Termux 套件 | Pi runtime |
| Pi | 維護中的 `@earendil-works/pi-coding-agent` npm 套件 | 原生預設，由 `installCodingAgents` 控制 |
| Herdr | 固定版本上游 Linux static binary | 明確選用的原生實驗 |
| Codex | 完整固定版本官方 Linux-musl package 與 companions | 第一台裝置已安裝，但正常 sandbox 在該裝置失敗 |
| Claude Code | 選用 PRoot distro 內的官方 Linux installer | 僅指南；repo 沒有原生 installer |
| Gemini CLI、OpenCode、OMP | 未來相容性工作 | 不自動安裝 |

Termux 套件針對 Android 建置；有原生套件時，優先用 `pkg`，不要換成一般 Linux
release asset。官方 recipes 包含
[chezmoi](https://github.com/termux/termux-packages/blob/master/packages/chezmoi/build.sh)
與 [Starship](https://github.com/termux/termux-packages/blob/master/packages/starship/build.sh)。
偏好 Neovim 時，也可以另外安裝其 Termux 套件。

## Pi

Pi 預設啟用。上游 Termux 指南使用維護中的套件名稱，並停用依賴的 lifecycle
scripts 安裝：

```sh
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```

bootstrap 固定並驗證 Pi 最上層 npm tarball 的版本、大小與 SHA-256；
transitive dependencies 仍由 npm 依一般 registry 流程解析，並非完整依賴鎖定。
一般 setup 後不必重複執行上游安裝指令。到專案目錄啟動 `pi`，
自行完成 provider 登入。電腦上的 API token 或 provider login 不會被複製。
後續 setup 若不選 Pi，使用 `--install-coding-agents false`；不會解除安裝既有
工具。


第一台裝置上的獨立 Pi 0.85.1 UI 在沒有憑證的情況下成功啟動，顯示
`No models available` / `/login`。限時 smoke test 到期以 124 結束；沒有驗證
正常離開、provider 登入或 model call。這是 UI 啟動結果，不是已登入的 agent
session。

文字剪貼簿整合需要 Termux:API Android app 與 `termux-api` 指令套件兩者。
Pi 在 Termux 不支援圖片剪貼簿貼上。companion 為選用項目，基本 terminal 工作
不需要 Android 裝置權限。參考 [Pi Termux 指南](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/termux.md)。

電腦端 `--api` 選項安裝 Android companion APK。需要原生指令時，在 Termux
明確同步並安裝：

```sh
pkg update && pkg upgrade -y && pkg install -y termux-api
```

## 原生 Herdr 與 Codex 實驗

明確選用其中一個或兩個：

```sh
# 電腦端：
just setup --with herdr,codex

# 或在 Termux clone 內：
bash bootstrap.sh packages --with herdr,codex
```

新下載使用固定版本上游 asset，驗證大小與 SHA-256。既有指令會保留，不直接
覆蓋，也不宣稱它與固定候選版本相同。選用工具失敗會與基礎
安裝結果分開報告。驗證 Herdr 時仍保留 tmux。版本字串只代表執行檔成功啟動，
不代表 session、認證或 agent 工具功能正常。

唯讀分析顯示 Herdr v0.9.0 ARM64 binary 與 Codex v0.153.4 ARM64-musl binary
是沒有 dynamic interpreter 的獨立 ELF 執行檔，因此在 Android Linux kernel
直接執行有合理可行性。兩個已驗證 asset 後來都在第一台 ARM64 Android 裝置
成功執行 `--version`，但安裝進一步遇到 app 私有目錄 hard link 的
`Permission denied`。installer 已改成不覆蓋既有目標的 rename，並檢查是否跳過
移動，後續完整 setup 重跑已以 0 結束。Codex 現在安裝完整官方 distribution，
包含 code-mode host、rg、bwrap、zsh 與 manifest；archive/member 檢查保留內容
相符的受管理檔案，拒絕衝突檔案或 symlinks。僅主執行檔可啟動，不代表完整
package 已驗證，也不等於上游正式支援 Android。

Herdr 需驗證 shell pane、分割／resize、pane CLI 操作，以及透過原生 Termux
sshd 斷線再 attach。`$SHELL` 與 `$TMPDIR` 應使用實際 Termux 路徑。
部分 Linux helper 直接呼叫 `/bin/sh`；程序／CWD／agent 偵測也依賴 `/proc`
存取。這些功能可能與主要 terminal session 各自成功或失敗。
參考 [Herdr shell 選擇](https://github.com/herdrdev/herdr/blob/v0.9.0/src/pane.rs)
與 [Linux command helpers](https://github.com/herdrdev/herdr/blob/v0.9.0/src/platform/linux.rs)。


第一台裝置的 headless workspace probe 已通過 run/read/split；互動 SSH TUI
也接受指令，Ctrl+b q detach/reattach 後 marker 保留，但這是在**同一條 SSH
連線內**完成。實體／網路斷線恢復與互動 resize 仍是另外的未驗證項目。

Codex 要驗證 provider 登入、DNS/TLS、檔案操作、shell/PTY 行為，以及原本的
sandbox。目前官方 Linux sandbox 使用 bubblewrap 與 seccomp，需要 host kernel
支援。無法初始化時，就將此項判為失敗，不要關閉 sandbox 後宣稱 probe 成功。
參考[官方 Codex CLI 文件](https://learn.chatgpt.com/docs/codex/cli)
與[官方 sandbox 文件](https://learn.chatgpt.com/docs/sandboxing)。


測試的 Android 15 裝置可啟動完整 Codex 0.153.4 package，但原本的 sandbox
因以下原始錯誤停止：

```text
bwrap: Can't read /proc/sys/kernel/overflowuid: Permission denied
```

這是已確認的 sandbox 啟動失敗，不證明 user namespaces 已停用；沒有使用
bypass。安裝隨附 helper 可補齊 package，但不會消除已觀察到的裝置限制。
此裝置的 Codex 不列為可正常使用 sandbox 進行 coding 的狀態。

Android 執行政策依 app build 與裝置而異。Termux 的 system-linker execution
模式無法載入 static binaries，不應修改 Android 防護來讓候選工具通過。
參考 [Termux 執行限制](https://github.com/termux/termux-exec-package/blob/master/site/pages/en/projects/docs/technical/index.md)。

## Claude 與其他 agents

分析的 Claude Code 2.1.263 Linux ARM64-musl 套件指定
`/lib/ld-musl-aarch64.so.1` 作為 loader，並非獨立的 static binary。
一般 Termux 檔案系統沒有這種 Linux 路徑配置。目前 npm 包裝也會啟動特定平台
的原生執行檔，不能將以前的純 JavaScript workaround 當作可靠預設。
請使用[選用 Linux 使用者環境指南](proot.md)與上游
[Claude 安裝說明](https://code.claude.com/docs/en/setup)。

Gemini 上游已有 Android 相關修正，但 runtime 依賴仍需裝置驗證。
OpenCode 與 OMP 目前的原生依賴針對 Linux/macOS/Windows 發布；即使已有原生
Bun，仍不代表這些依賴相容。這些工具列為未來工作，不藏在自動 fallback installer
裡。參考 [Gemini 安裝指南](https://geminicli.com/docs/get-started/installation/)、
[OpenCode 套件 metadata](https://registry.npmjs.org/opencode-ai/latest)、
[OMP 原生依賴](https://registry.npmjs.org/@oh-my-pi/pi-natives/latest)。
