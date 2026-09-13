# 安裝與維護

使用 F-Droid 版原生 Termux，Android 7 以上；本 repository 的第一個 runtime
目標是 ARM64。電腦端 helper 支援 macOS 與 Linux。Windows 使用者可以先採用
下方的裝置端手動安裝流程。

## 一次選好需要的工具

電腦端在這個 clone 內，一行選用 Herdr 0.9.0、dev-cli 0.2.33、Pi 0.85.1
與 Codex 0.153.4：

```sh
uv run --script scripts/host.py setup --with herdr,codex,dev --install-coding-agents true
```

全新的原生 Termux shell 可直接貼上
[README 的裝置端一行安裝指令](https://github.com/daviddwlee84/dotfiles-Termux#one-line-setup-herdr--dev-cli--coding-agents)。
如果裝置上已有 checkout，在 Termux 執行：

```sh
cd "$HOME/.local/share/dotfiles-Termux" && bash bootstrap.sh update && bash bootstrap.sh packages --with herdr,codex,dev --install-coding-agents true
```

只要 Herdr/dev-cli、不選 Codex 時用 `--with herdr,dev`；Pi 仍啟用。
`--with` 取代保存的選用清單，既有 binary 會保留。安裝成功與
[runtime 支援](tools.md) 分開判斷，尤其是已觀察到的 Codex sandbox 失敗。

setup 後可在任意目錄執行 `chezmoi diff/apply/update` 管理受管理設定；
新增選用工具與完整套件同步則用 `packages`。dev config 由使用者管理，
Herdr config 是只建立一次的 seed。開啟新 Bash shell 後就會載入 dev 的目錄
切換與補全功能。

## 指令要在哪裡執行？

完整 provisioning 與 SSH helper 都在公開的
[dotfiles-Termux repository](https://github.com/daviddwlee84/dotfiles-Termux)，
包含 `justfile`、`scripts/host.py` 與 `scripts/host-deps.sh`。可以單獨 clone
使用，不需要取得 umbrella repository。`dotfiles-all` 的 recipes 只是把參數
轉交給這些公開 helpers。

以下都是在 **macOS/Linux 電腦端**執行的指令：

| 工作 | 在 `dotfiles-all/` | 在公開 `dotfiles-Termux/` clone | 不用 just，在公開 clone 內 |
| --- | --- | --- | --- |
| 主機依賴 | `just termux-host-deps` | `just host-deps` | `sh scripts/host-deps.sh` |
| 列出裝置 | `just termux-devices` | `just devices` | `uv run --script scripts/host.py devices` |
| 設定 Android | `just termux-setup` | `just setup` | `uv run --script scripts/host.py setup` |
| 連線 Android | `just termux-ssh` | `just ssh` | `uv run --script scripts/host.py ssh` |
| 主機／裝置健康檢查 | `just termux-doctor` | `just doctor` | `uv run --script scripts/host.py doctor` |
| 維護檢查 | `just check-termux` | `just check` | 參考[驗證指南](verification.md) |

standalone justfile 沒有定義 umbrella 的 `termux-*` recipe 名稱。
在 **Android 的 Termux 內**，從裝置 repository working tree 執行
`bash bootstrap.sh setup` 完成首次 target setup；裝置健康檢查則用
`just target-doctor` 或 `bash bootstrap.sh doctor`。即使在 Android 打開同一個
repository，standalone 的 `just setup`、`just ssh`、`just doctor` 仍是電腦端
recipes。

已安裝的 `termux-ssh`（**前面不加 just**）是另一個裝置端 helper：
`termux-ssh status|start|stop` 管理平板自己的 sshd。私鑰與配對狀態留在電腦，
但 helper 程式本身是公開的。

## 從電腦透過 ADB 安裝

1. 在電腦 clone `https://github.com/daviddwlee84/dotfiles-Termux.git`。
2. 執行 `sh scripts/host-deps.sh` 檢查依賴。支援的 macOS 與 Debian/Ubuntu
   主機可明確執行 `sh scripts/host-deps.sh --install` 安裝缺少的工具。
   Linux USB 權限設定是另外的選項：`sh scripts/host-deps.sh --usb-rules`。
3. Android 開啟開發人員選項與 USB 偵錯，接上可傳資料的 USB 線，解鎖螢幕，
   並允許這台電腦的 ADB key。
4. 在 clone 內執行：

```sh
export PATH="$HOME/.local/bin:$PATH"
uv run --script scripts/host.py devices
uv run --script scripts/host.py setup
uv run --script scripts/host.py ssh
uv run --script scripts/host.py doctor
```

依賴 helper 不要求或安裝 `just`。已有 just 時，可用 `just devices`、
`just setup`、`just ssh` 與 `just doctor` 作為捷徑。暫時的 `PATH` 設定涵蓋
`~/.local/bin` 下的 uv，不會修改 shell profile。

同時連接多台裝置時，使用 `--serial SERIAL` 指定一台。只有需要變更初始預設值
或已保存的選擇時，才加入下列選項：

```sh
uv run --script scripts/host.py setup --serial SERIAL --manual
uv run --script scripts/host.py setup --serial SERIAL --api
uv run --script scripts/host.py setup --serial SERIAL --ssh-mode adb
uv run --script scripts/host.py setup --serial SERIAL --with herdr,codex
uv run --script scripts/host.py setup --serial SERIAL --with herdr,dev
```

需要配對時，`--manual` 顯示一次性指令，由你貼到新的 Termux shell。
`--api` 加裝 Termux:API companion。SSH 預設在 port 8022 提供 LAN 存取；
`--ssh-mode adb` 改成僅綁定 loopback。`--no-boot` 關閉受管理的 Boot 整合；
`--wake-lock` 明確選擇保持 CPU 喚醒。setup 預設等待 900 秒；首次套件同步較慢時
可以增加 `--timeout`。

helper 驗證固定版本 APK 的大小與 SHA-256，安裝選定的 F-Droid 來源 apps。
首次配對時再開啟 Termux，簡短的配對指令只送入新 shell；無法確認新 shell
時改成手動貼上，不會對任意既有工作輸入指令。

配對透過暫時的 USB 連線傳入專用 SSH **公鑰**，並記錄裝置的 SSH host key。
對應私鑰留在電腦上。配對後，其餘安裝透過 USB 轉送的 SSH 進行，不需要手機的
LAN IP。Android 有對話框時請保持裝置解鎖。中途停止後，重跑相同指令即可接續。
重跑會先嘗試已保存且正常的 SSH，只有需要時才回到新 shell／手動配對。
保存狀態與管理範圍詳見 [SSH 與開機啟動](ssh.md)。

serial 也可以放在子指令之前：

```sh
uv run --script scripts/host.py --serial SERIAL setup --manual
uv run --script scripts/host.py --serial SERIAL ssh -- uname -a
```

切換 umbrella 與 standalone clone 時，依上方的指令位置表選擇名稱。
umbrella 原本的 `just apply` 仍然套用電腦原生 Unix/Windows 設定。

## APK 來源與簽章

自動流程使用 F-Droid 簽章來源的 Termux 與 companion。F-Droid app 方便日後
更新；已安裝的 APK 不需要它才能執行。開啟 F-Droid 後，先讓 repository index
更新完再搜尋 Termux。

Termux、Termux:Boot 與 Termux:API 必須來自**同一來源**。既有 GitHub 簽章 app
不能用 F-Droid 簽章 APK 覆蓋更新。setup 遇到簽章衝突會停止並保留資料。
若你決定切換來源，請先匯出 Termux 資料，再依上游說明遷移；helper 不會為了
排除衝突而解除安裝 app。目前 Google Play 分支仍屬實驗性，不在此 helper 的 APK
流程內。參考 [Termux 官方安裝說明](https://github.com/termux/termux-app#installation)。

## 在裝置上手動安裝

1. 從 [f-droid.org](https://f-droid.org/) 下載 F-Droid。Android 詢問時，允許
   使用的瀏覽器／檔案管理器安裝下載的 app。
2. 更新 F-Droid repositories，安裝
   [Termux](https://f-droid.org/en/packages/com.termux/) 與
   [Termux:Boot](https://f-droid.org/en/packages/com.termux.boot/)。
   需要剪貼簿／裝置整合才加裝 Termux:API。Android 詢問時允許 F-Droid 安裝 app。
3. 開啟 Termux，等內建 bootstrap 完成。另開啟一次 Termux:Boot，讓 Android
   允許其 boot receiver 執行。
4. 在 Termux 同步套件、取得 Git、clone repository 並安裝：

```sh
pkg update && pkg upgrade -y && pkg install -y git
mkdir -p "$HOME/.local/share"
git clone https://github.com/daviddwlee84/dotfiles-Termux.git "$HOME/.local/share/dotfiles-Termux"
cd "$HOME/.local/share/dotfiles-Termux"
bash bootstrap.sh setup
```

尚未提供授權公鑰時，本機環境仍會完成安裝，SSH 顯示 `pending-key`。
若要啟用 SSH，將可信任電腦的 public-key 那一行放到裝置的 `$HOME/host.pub`，
再執行：

```sh
bash bootstrap.sh setup --authorized-key-file "$HOME/host.pub"
```

只複製 `.pub` 檔案，不要將私鑰傳到 Android，也不要 commit 配對資料。
詳見[手動 LAN 存取](ssh.md#manual-lan-access)。

## HOME、PREFIX 與 chezmoi source

此 repo 支援的原生 Termux app 路徑中，`~` 就是 `$HOME`：

| 層級 | 位置 | 用途 |
| --- | --- | --- |
| 裝置 HOME | `/data/data/com.termux/files/home` | 個人檔案與 dotfile 部署目的地 |
| 套件 PREFIX | `/data/data/com.termux/files/usr` | 原生執行檔在 `$PREFIX/bin`，套件設定在 `$PREFIX/etc` |
| Repository working tree | `$HOME/.local/share/dotfiles-Termux` | Git checkout、bootstrap、scripts、justfile 與 docs |
| chezmoi 有效 source | `$HOME/.local/share/dotfiles-Termux/home` | 由 repository 的 `.chezmoiroot` 指定的 templates |
| 預設 chezmoi 設定檔 | `$HOME/.config/chezmoi/chezmoi.toml` | 保存 source 位置與功能選擇 |

repository 的 `home/` 是**來源模板目錄**，不是 Android 的 `$HOME`。
`.chezmoiroot` 內容只有 `home` 這個字，因此 `chezmoi source-path` 與
`.chezmoi.sourceDir` 指向 checkout 裡的 `home/`，`.chezmoi.workingTree`
則指向 checkout 根目錄。

使用 `.local/share/dotfiles-Termux` 而非 chezmoi 通常的
`.local/share/chezmoi`，是本 bootstrap 的約定，不是 Termux 或 chezmoi 的
強制要求。固定位置讓 bootstrap 與 SSH-resume helper 找得到 repository，
也讓 scripts 和 templates 放在同一份 checkout。無需另外在預設 chezmoi
位置建立第二份 clone；既有無關 chezmoi 狀態會保留，不會被默默搬移或覆蓋。

setup 中的 `scripts/manage.sh` 以明確 source（working tree）與 destination
（`$HOME`）執行 `chezmoi init`。`home/.chezmoi.toml.tmpl` 將設定檔的
`sourceDir` 寫成 **working-tree 根目錄的絕對路徑**；chezmoi 再依 `.chezmoiroot`
選定有效的 `home/` source。同時保存功能 data 與只允許 fast-forward 的更新
helper。初始化後，在任意目前目錄執行一般 chezmoi 指令，都會找到保存的 source。
可以在 Termux 檢視路徑：

```sh
printf 'HOME=%s\nPREFIX=%s\n' "$HOME" "$PREFIX"
chezmoi source-path
chezmoi execute-template '{{ .chezmoi.workingTree }}'
```

`bootstrap.sh` 是裝置首次安裝的入口。在既有 clone 中執行時，它會轉交給
`scripts/manage.sh`；若收到的是獨立 bootstrap 檔案，則先取得固定位置的 clone。
電腦 `setup` 透過已配對 SSH 傳送此入口；上方手動流程則 clone 同一個公開 repo
後，在裝置本機執行。首次流程安裝套件並初始化 chezmoi；日常
`chezmoi diff`、`chezmoi apply`、`chezmoi update` 都只處理設定。

## 設定與套件更新

原生套件政策將經常進行的 dotfile 更新與完整套件同步分開：

| Termux clone 內的操作 | 行為 |
| --- | --- |
| `chezmoi diff` | 預覽實際受管理檔案差異；init 後可在任意目錄執行 |
| `just diff` | 預覽 bootstrap 設定／dry-run 選擇；此 recipe 不顯示檔案 diff |
| `just apply` / `bash bootstrap.sh apply` | 套用設定，不升級套件 |
| `bash bootstrap.sh update` | Git source 僅 fast-forward，再套用設定 |
| `just packages` | 完整同步 Termux 套件，再安裝已選工具 |
| `just upgrade` | 完整同步原生套件；既有選用工具執行檔保持原樣 |
| `bash bootstrap.sh setup` | 首次安裝，或明確重跑完整 setup |
| `bash bootstrap.sh doctor` | 查看裝置端狀態 |

一般 `chezmoi apply` 與 `chezmoi update` 不會安裝／升級套件。
`--config-only` 選擇僅套用設定。Termux 不支援 partial upgrade，不要將完整同步
改成只升級個別依賴。套件操作需要正常的 mirror；下載失敗時先修復 mirror／網路，
再重跑明確的套件操作。參考 [Termux 套件管理](https://github.com/termux/termux-packages/wiki/Package-Management)。

裝置端選擇會保留至下次執行。省略 `--with` 保留 Herdr/Codex/dev-cli 選擇；提供它會取代
選擇清單，但不解除安裝既有工具。Pi 由 `--install-coding-agents true|false`
控制，預設 true。電腦與裝置端其他布林選項包含 `--install-ssh-server`、
`--install-termux-boot` 與 `--termux-wake-lock`。

值已提供或採用預設值時可加上 `--non-interactive`。既有、無關的 chezmoi source
會保留；遇到 source 衝突時應明確解決，不要刪除另一套設定。

`~/.config/dotfiles-termux/settings` 由 chezmoi init data 渲染，不要直接編輯。
若只調整保存設定、不同步套件，執行 `chezmoi edit-config`，修改對應 `[data]`
值，再執行 `chezmoi apply`。

需要重新檢視原生 init 問題時，執行 `chezmoi init --prompt`，再執行
`chezmoi apply`。保存的值如下：

| Data key | 預設 | Prompt |
| --- | --- | --- |
| `installSshServer` | `true` | Install SSH server |
| `sshMode` | `"lan"` | SSH access mode |
| `sshPort` | `"8022"` | SSH port |
| `installTermuxBoot` | `true` | Start SSH with Termux Boot |
| `termuxWakeLock` | `false` | Acquire wake lock at boot |
| `installCodingAgents` | `true` | Install coding agents (Pi) |
| `optionalTools` | `""` | Optional tools (herdr,codex,dev or empty) |

init data 的套件選擇在下次明確的 setup/packages/upgrade 生效；僅套用設定不會
下載工具。電腦 `setup` 只在新設定採用預設值；重跑會保留裝置選擇，只有明確
提供的選項會變更它們。

電腦端的 `--install-ssh-server`、`--install-coding-agents`、
`--install-termux-boot` 與 `--termux-wake-lock` 都接受 `true|false`。
`--no-boot` 等同 `--install-termux-boot false`，`--wake-lock` 等同
`--termux-wake-lock true`。若明確停用 SSH，setup 會保存此最終狀態，本機
Termux 仍可使用。

host `doctor` 即使無法選定裝置，也會報告已安裝的主機能力，並以非零狀態提供
後續指示。對已配對且可連線的裝置，也會透過 SSH 執行原生 target doctor。
裝置探索失敗不代表沒有連接裝置。

## 找不到 which 或 file

`which` 是[獨立的 Termux 套件](https://github.com/termux/termux-packages/blob/master/packages/which/build.sh)；安裝 `util-linux` 不會提供它。baseline 現在
明確包含 `which` 與 `file`。只想查看指令位置時，不需要等 which 安裝，Bash
本來就有 `command -v git` 與 `type -a git`。

較舊的 checkout 先用 `chezmoi update` 更新 source，再到
`$HOME/.local/share/dotfiles-Termux` 執行 `just packages`，完整同步原生套件並
補上缺少的 baseline 指令。一般 chezmoi apply 刻意不安裝新加入的套件。

## 裝置端網路失敗

電腦下載 APK 與裝置存取套件／GitHub 使用不同網路路徑。首次裝置測試中，USB
SSH 已可連線，但 GitHub TLS 請求出現 EOF 或 timeout。使用者自行在裝置啟用
VPN 後，GitHub 存取與 `git ls-remote` 成功，setup 得以接續。

這項觀察不能確認原本 TLS 失敗的原因。程式沒有修改全域 VPN、proxy 或 DNS
設定。請先解決裝置連線，再重跑 setup；可重用已保存的 SSH 配對。目前尚未
實作離線 bundle／安裝模式。
