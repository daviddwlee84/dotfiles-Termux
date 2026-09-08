# SSH 與開機啟動

SSH 預設啟用 **LAN 模式**，使用 **8022** port 與公鑰認證。沒有授權公鑰時，
SSH 保持 `pending-key`，本機工具仍可完成安裝。setup 不會啟用密碼登入。

## USB 存取與配對

完成電腦輔助安裝後，使用：

```sh
just ssh
just ssh --serial SERIAL
```

host helper 建立暫時的 ADB forward，並以配對取得的 SSH host key 驗證裝置。
結束時只清除此 invocation 建立的 mapping。每台裝置使用獨立 identity，不修改
你原有的 SSH 設定或其他電腦上的 authorized keys。

電腦端配對資料位於 `${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles-termux`，
每台選定裝置有衍生出的子目錄，包含產生的私鑰、known-hosts 與連線 metadata，
並使用私有目錄／檔案權限。請保護此目錄，不要放進 Git。刪除電腦端私鑰會失去
該配對 identity，但不會自動撤銷裝置上已授權的公鑰。

app reset 後若 SSH host key 改變，請先確認原因。不要透過關閉 host-key checking
或刪除無關 known-hosts 項目解決。helper 保留既有信任，不會默默接受另一台裝置。

## LAN 與僅 USB 模式

| 模式 | 監聽 | 連線方式 |
| --- | --- | --- |
| `lan`（預設） | IPv4 `0.0.0.0:8022` | ADB-forwarded helper 或裝置 LAN IP |
| `adb` | IPv4 `127.0.0.1:8022` | ADB-forwarded helper |

電腦 setup 時選擇僅 USB：

```sh
just setup --ssh-mode adb
```

在裝置的 repository clone 內變更模式：

```sh
bash bootstrap.sh apply --ssh-mode adb
# 需要時恢復 LAN 存取：
bash bootstrap.sh apply --ssh-mode lan
```

若變更 port，請一致使用 `--ssh-port PORT`。如果其他 SSH server 已占用該 port，
這是需要處理的衝突，不代表可以停止對方的服務。

<a id="manual-lan-access"></a>
## 手動 LAN 存取

手動安裝時，在電腦上選擇既有 SSH key，或建立新的專用 key：

```sh
ssh-keygen -t ed25519 -f "$HOME/.ssh/termux-dev"
```

只將 `termux-dev.pub` 複製到 Termux 的 `$HOME/host.pub`。
在裝置 clone 內授權並查看狀態：

```sh
bash bootstrap.sh setup --authorized-key-file "$HOME/host.pub"
bash bootstrap.sh doctor
whoami
```

首次 setup 後，也可用 `termux-ssh authorize "$HOME/host.pub"` 加入 key 並
啟動受管理服務，不同步套件。`termux-ssh status`、`termux-ssh start` 與
`termux-ssh stop` 只管理該服務，不影響無關 sshd。

使用顯示的 Termux 使用者名稱與 Android Wi-Fi IP：

```sh
ssh -p 8022 -i "$HOME/.ssh/termux-dev" TERMUX_USER@DEVICE_LAN_IP
```

首次手動連線時，先核對 SSH 顯示的 host-key fingerprint 與裝置 host 公鑰，再
接受連線。手動 LAN 安裝不會自動建立電腦 helper 另外保存的配對信任。

在裝置顯示 fingerprint：

```sh
ssh-keygen -lf "$PREFIX/etc/ssh/ssh_host_ed25519_key.pub"
```

## 受管理檔案

本 repository 管理 `~/.config/dotfiles-termux/sshd_config` 與
`~/.local/state/dotfiles-termux/` 下自己的程序狀態。提供有效公鑰時會附加授權，
不移除 `authorized_keys` 中無關的內容，既有 SSH host keys 也會保留。
repo 只控制自己的 daemon/PID 與 Boot hook，不會停止其他 sshd 或取代全域
OpenSSH 設定。

裝置選項保存在 `~/.config/dotfiles-termux/settings`。若要停止管理 repo 的
SSH 服務，以 `--install-ssh-server false` 套用設定。這不會解除安裝 app，也不會
移除其他 SSH 服務。

## Termux:Boot 與 Android 背景行為

Boot 整合預設啟用。請從與 Termux 相同簽章來源安裝 Termux:Boot，並且
**開啟一次**。repository 只建立 `~/.termux/boot/50-dotfiles-termux` 這個 script；
其他 script 仍由你管理。Boot app 會在裝置開機後依名稱順序執行 script。
參考[上游 Boot 說明](https://github.com/termux/termux-boot#usage)。

wake-lock 預設關閉。裝置端可用 `--termux-wake-lock true`，電腦 setup 可用
`--wake-lock` 明確開啟。wake-lock 可能增加耗電，不能保證程序不受 Android
force-stop 或廠商背景限制影響。

電池最佳化豁免與通知／儲存權限都是另外的 Android 選擇。需要長時間 session 時，
請檢查該裝置的 Termux 電池設定，並實測關閉螢幕後重新連線。
terminal multiplexer 只會在程序仍存活時保留 SSH 斷線前的 session；重開機或
Android 終止程序是另一回事。參考 [Termux 程序模型](https://github.com/termux/termux-packages/wiki/Termux-execution-environment#daemon-c-function)。
