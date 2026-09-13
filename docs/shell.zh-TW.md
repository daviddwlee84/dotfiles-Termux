# Shell 與設定

全新 setup 使用原生 Termux zsh。既有環境保留已保存的 shell；舊設定若沒有
`primaryShell`，則沿用目前的登入 shell。Bash 仍會安裝，bootstrap、套件、SSH
與 Boot 管理腳本都明確由 Bash 執行。兩種 shell 都有下列共用 helpers。

## 選擇 shell

```sh
# 在已更新的 Termux clone 內：
bash bootstrap.sh packages --primary-shell zsh
# 切回 Bash，不解除安裝套件：
bash bootstrap.sh apply --primary-shell bash
# 電腦端 setup 的等效選項：
uv run --script scripts/host.py setup --primary-shell zsh
```

選擇保存在 chezmoi 的 `primaryShell`。僅套用設定不會安裝缺少的 zsh 或 plugins；
缺少依賴時會明確報告並保留登入 shell。`packages` 先完整同步原生套件、安裝固定
版本 assets，再進行切換。原生環境 guard 與所有管理腳本的 shebang 仍要求 Termux Bash。

新的 Termux／SSH login 使用所選 shell，既有 panes 與 multiplexer servers 繼續
執行。Herdr 未經自訂的原始 seed 會跟隨選擇供新
session 使用；自訂 Herdr 設定則保留，並提示明確設定 `terminal.default_shell`。

## 互動功能與 helpers

zsh 採精簡 Oh My Zsh，啟用 `git` plugin、zsh-autosuggestions、
zsh-syntax-highlighting、官方 zsh-completions、快取的 dev 補全與既有簡潔 Starship。
使用 Emacs 操作模式：Tab 補全、Ctrl+R 搜尋 history，游標在指令末端時按 Right
接受灰字建議。zsh 使用獨立的 `.zsh_history`，不轉換 Bash history。zsh 的 glob
與變數拆詞規則不同；需要 Bash 語意的腳本用 `bash script.sh` 執行。

```sh
lg                              # 在目前 repository 開啟 lazygit
y                               # 瀏覽檔案；q 離開後切換到所選目錄
y "$HOME"                       # 從指定目錄開啟 Yazi
yazi                            # 直接啟動，不改變外層 shell 目錄
abspath                         # logical 目前目錄，和 pwd 相同
abspath 'file with spaces' ../x  # 絕對路徑；不要求檔案已存在
abspath -r link                  # 解析 symlink；目標必須存在
abspath -t "$HOME/src"           # ~/src
abspath -- -filename             # 名称以 - 開頭
source-rc                        # 重新載入目前 shell 的 rc 與 helpers
reload                           # source-rc 的 alias
chezmoi-cd                       # 進入有效的 chezmoi source（home/）
```

既有的 `lg`／`y` 指令、alias 或 function 會保留。未自訂時，
`lg` 是 `lazygit` 的 alias；`y` 會把參數傳給 Yazi，成功離開且有回傳目錄時才切換
shell 目錄。按 `Q` 離開會保留原目錄；暫存 cwd 檔案會在結束後移除，啟動失敗時
保留目前目錄並回傳錯誤碼。兩者都納入原生 `pkg` 基礎套件，shell 啟動不下載。
參考 [Yazi 官方 wrapper](https://yazi-rs.github.io/docs/quick-start/#shell-wrapper)。

rc 保留原內容，再加入管理區塊。Bash 既有的 login forwarding 不變；zsh login
設定載入共用 PATH/helpers，不載入互動 plugins。重複 source 不會重複包裝 plugins
或註冊 prompt hooks。`reload` 明確重跑目前 rc，也包含使用者內容。持久覆寫可放
`~/.config/dotfiles-termux/local.sh`（Bash）或 `local.zsh`（zsh）。

Oh My Zsh／plugins 放在 `~/.local/share/dotfiles-termux/zsh` 的專用版本目錄。
lockfile 固定 commit、SHA-256 與大小；只有明確的套件操作安裝新固定版本。
一般 chezmoi apply 與 shell 啟動不下載、不自動更新。保留補全安全檢查，compdump
與 dev 產生的腳本使用獨立快取；dev binary 路徑或 mtime 改變時才重新產生快取。

## 啟動速度實測

2026-09-13 在 ARM64 Android 15 平板上，以每種 shell／目錄 30 次交錯暖啟動驗證。
量測原生互動 rc 到第一個 prompt，不包含 SSH 傳輸與 login profiles；冷快取指清空
測試專用的 completion/dev/prompt cache，沒有清除 OS cache。

| 位置 | 受管理 Bash 中位數／P95 | zsh 中位數／P95 | zsh 冷快取 |
| --- | --- | --- | --- |
| HOME | 116 / 133 ms | 186 / 204 ms | 694 ms |
| Git repository | 119 / 139 ms | 190 / 208 ms | 692 ms |

門檻為中位數額外 ≤100 ms、P95 額外 ≤200 ms、冷快取第一個 prompt 在一秒內。
移除多餘的外部快取檢查後已通過，所以不需要退回原生 zsh-only 方案。在 Termux 重現：

```sh
python scripts/benchmark-shell.py --managed-bash --candidate-config home/dot_config/dotfiles-termux --repo .
```

## Python 與 uv

Python、`uv`、`uvx` 都由官方 `pkg` 套件提供。只建立一次的
`~/.config/uv/uv.toml` 使用 `python-preference = "only-system"`、
`python-downloads = "never"`、`link-mode = "copy"`，選用原生 Termux Python，
避免 Android app 儲存空間上已觀察到的 hardlink 失敗。後續本機修改會保留。

```sh
uv --version
uv venv .venv
uv pip install --python .venv/bin/python packaging==25.0
uv run --no-project --with packaging==25.0 python -c 'import packaging; print(packaging.__version__)'
```

實機已用 Python 3.14.6、uv 0.12.13 通過建立 venv 與 PyPI 安裝。需要 native
extensions 的套件仍需 Android 相容的原始碼／依賴；這不代表每個 PyPI wheel
都支援。系統依賴及 Python／uv 升級仍由 `pkg` 管理。

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
chezmoi diff
just apply
bash bootstrap.sh update
```

這些操作不會升級套件。需要完整同步時，明確執行 `just packages` 或
`just upgrade`。若新設定需要新的依賴，另外進行套件同步。

Termux 使用 Bionic libc。Linux ARM64 下載檔不一定是原生 Termux 套件：CPU
架構相同，不代表 loader、路徑、DNS、PTY 或 sandbox 相容。已有套件的工具優先
使用 `pkg`；實驗請依[agent 相容性指南](tools.md)進行。
