# Shell 與設定

原生 shell 使用 Termux Bash。保留實際的 `$PREFIX` 與 `$HOME`，不要假設
`/usr/bin`、`/etc` 或桌面 Linux 的使用者名稱。裝置端不需要 root、Ansible、
Homebrew 或桌面 shell framework。

chezmoi 管理 `home/` source root。bootstrap 保留既有 shell 內容並加入受管理
設定，不會把另一套 chezmoi source 默默改成此 repository。先以 `just diff`
查看差異，再用 `just apply` 套用。使用者擁有的設定與無關 SSH keys 都會保留。

Starship 在互動式 Bash session 初始化。Vim、Git 與 tmux 提供編輯器、
版本控制與 multiplexer 基礎，無需先完成選用 agent 的設定。驗證 prompt 與
terminal 行為時，請同時測試本機 Termux tab 與新的 SSH login。

## 原生路徑

| 用途 | 位置 |
| --- | --- |
| 家目錄與專案 | `$HOME`（通常是 `/data/data/com.termux/files/home`） |
| Termux 執行檔 | `$PREFIX/bin` |
| Termux 套件設定 | `$PREFIX/etc` |
| 暫存檔案 | `$TMPDIR` |
| Dotfile source root | clone 的 `home/` |
| 本 repository 保存的選項 | `~/.config/dotfiles-termux/settings` |

專案 checkout 請保留在 app 私有儲存空間。Android 共享儲存空間可能掛載為
`noexec`，無法保留完整 Unix 檔案語義，不適合放 Git repositories 或執行檔。
需要交換檔案時才另外執行 `termux-setup-storage`；bootstrap 不會要求廣泛儲存
存取。參考[官方檔案系統／執行說明](https://github.com/termux/termux-packages/wiki/Termux-execution-environment#file-execution-and-special-file-features-not-allowed-in-external-storage)。

## 日常操作

```sh
# 在 Termux repository clone 內：
just diff
just apply
bash bootstrap.sh update
```

這些操作不會升級套件。需要完整同步時，明確執行 `just packages` 或
`just upgrade`。若新設定需要新的依賴，另外進行套件同步。

Termux 使用 Bionic libc。Linux ARM64 下載檔不一定是原生 Termux 套件：CPU
架構相同，不代表 loader、路徑、DNS、PTY 或 sandbox 相容。已有套件的工具優先
使用 `pkg`；實驗請依[agent 相容性指南](tools.md)進行。
