# 在 Android 使用原生開發工具

dotfiles-Termux 將 Termux 設定成小型開發環境，並提供 macOS/Linux helper，
透過 ADB 完成首次安裝。這是受到 dotfiles-iSH 啟發的獨立實驗性 repository，
使用原生 Termux 套件，不共用 iSH 的 Alpine bootstrap。

從[安裝指南](setup.md)開始。預設包含 chezmoi、Bash、Starship、Git、
Vim、tmux、開發工具、Node.js 與 Pi。公鑰 SSH 與 Termux:Boot
整合預設啟用；wake-lock 預設關閉。Herdr 與 Codex 是明確選用的原生實驗，
必須另外完成[相容性驗證](tools.md)。

Termux 使用 Android 的 Linux kernel 與 app 私有檔案系統，不是 Debian VM；
一般 ADB shell 也不是 Termux session。專案與執行檔應放在 Termux `$HOME`，
不要放在共享儲存空間。參考[官方執行環境說明](https://github.com/termux/termux-packages/wiki/Termux-execution-environment)。

| 工作 | 電腦端 | Termux clone 內 |
| --- | --- | --- |
| 尋找、連線 | `just devices`、`just ssh` | — |
| 首次安裝 | `just setup` | `bash bootstrap.sh setup` |
| 查看狀態 | `just doctor` | `bash bootstrap.sh doctor` |
| 預覽、套用設定 | — | `just diff`、`just apply` |
| 同步套件 | — | `just packages` |
| 完整升級套件 | — | `just upgrade` |

[SSH 指南](ssh.md)說明 LAN 與僅 USB 存取。
[選用 Linux 使用者環境指南](proot.md)介紹需要 Linux distribution 的 Claude Code
或其他工具如何使用 PRoot。原生 bootstrap 不會自動安裝 PRoot。

桌面 CI 驗證 fixture、script 與渲染設定。CI 通過不代表 Android 裝置或 coding
agent session 已經實測。詳見[驗證層級](verification.md)。
