# 選用 Linux 使用者環境

工具需要一般 Linux distribution 時，例如 Claude Code 所需的 Linux loader
與檔案系統配置，可以使用 PRoot distro。這是手動、明確選用的 fallback。
原生 bootstrap 不會安裝 PRoot，也不會默默把 agent 指令改成進入 guest 執行。

保留 Termux 原生 sshd 作為入口，SSH 登入後再明確進入 guest。guest 的工具／
設定留在 guest，原生 Termux 的工具／設定留在 Termux。不要在 guest 內套用本
repository，也不要讓兩邊共用原生工具的私有狀態目錄。

## 準備相同架構的 guest

在 Termux 完整同步套件後，再安裝 PRoot-Distro：

```sh
pkg update && pkg upgrade -y && pkg install -y proot-distro
proot-distro install ubuntu:24.04 --name agents
proot-distro login agents
```

這裡的 guest 名稱只是範例，重用之前請先查看既有安裝。ARM64 手機請使用 ARM64
guest。目前 PRoot-Distro 支援 OCI images，不需要 Docker daemon 或裝置 root。
若安裝版本的 image 語法不同，請核對[上游 CLI 文件](https://github.com/termux/proot-distro#readme)。

在 Ubuntu guest 內：

```sh
apt update && apt full-upgrade -y
apt install -y ca-certificates curl git vim tmux
mkdir -p "$HOME/projects"
```

在此 guest 裡依 [Claude 官方 Linux 指南](https://code.claude.com/docs/en/setup)
安裝，保留 installer 的驗證。到 guest 專案啟動 `claude` 並自行完成登入。
Herdr 請依 [herdr.dev](https://herdr.dev/) 上游 Linux 安裝說明進行，確認 shell
pane 與 detach/reattach 正常後再依賴它工作。

Codex 也可以在 guest 依[官方 Linux 指南](https://learn.chatgpt.com/docs/codex/cli)
評估。Linux loader 能用不代表 agent sandbox 能用，仍需完成與原生實驗相同的
sandbox 驗證。

執行 `exit` 離開 guest；下次回來使用：

```sh
proot-distro login agents
```

若需要在 host SSH 斷線後保留工作，可從原生 Termux tmux session 啟動 guest，
再 detach 該 session。目前 PRoot-Distro 也支援 detached session 與 `ps`/`kill`
管理；使用此模式時請依其文件操作，並為長時間指令保留 logs。
既然原生 Termux SSH 已可進入 guest，不必為此再啟動第二個 guest sshd。

## 效能與限制

架構相同的 ARM64 guest 中，PRoot 改寫 syscall 路徑，不是模擬 ARM64 指令。
然而 syscall interception 仍有成本：套件安裝、編譯、Git 掃描與大量小檔案操作
可能明顯變慢。等待遠端模型回覆的 terminal session 是另一種負載，沒有適用所有
手機的固定變慢百分比。決定工作位置前，應用相同 checkout 與指令比較原生和
guest 的實際耗時。

PRoot 不會增加 kernel namespaces、cgroups 或真正 root 權限。個別長時間程序
可以運作，但完整 init system 與 service supervisor 通常不在支援範圍內。
Android 的電池／程序限制仍然存在。參考[官方限制](https://github.com/termux/proot-distro#limitations)。

因此 PRoot 不能補出 Codex 或 Claude sandbox 需要的 kernel 功能。原本的
sandbox 若失敗，就記錄失敗並改用支援的遠端電腦處理該 workflow，不要把關閉
sandbox 當成相容性修復。本 repository 的桌面 CI 不宣稱已驗證 guest runtime
或 agent 登入。
