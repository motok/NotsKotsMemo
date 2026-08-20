# Ubuntu Server 26.04 LTS インストールメモ

- Ubuntu Server 26.04 LTS にも慣熟せねば、ということで、インストールと初期設定をした。
- 2026-08-20 頃書いた。

## 対象

- Ubuntu Server 26.04 LTS をインストールしてみた。
  - ubuntu-26.04-live-server-amd64.iso

- ハードウェアとしては、 FreeBSD 上の bhyve VM として実行した。
  (うまく言えない)

## OS インストール

- ISO イメージから普通にインストール。
- インストールしたら、パッケージ更新
  ``` shell
  # apt update
  # apt upgrade
  ```
- 個人的な好みでパッケージ追加
  ``` shell
  # apt install nkf lv lftp
  ```

## ホスト名の初期設定

- インストール中にホスト名を入力するが、最左端のラベルだけしか入力できなかった。
- そのままでも構わないようなものだが、FQDN にしておく。
  ``` shell
  # hostnamectl (現在設定の表示)

  # hostnamectl set-hostnmae foo.example.com
  ```
- `/etc/hosts` で `foo` や `foo.example.com` が IP アドレスに解決できるようにしておく。
  ``` shell
  # vi /etc/hosts
  ```

## 時刻・タイムゾーンの初期設定

- デフォルトで chronyd が動作している模様。
- デフォルトでは UTC で動くので、日本時間に修正。
  ``` shell
  # timedatectl (現在設定の表示)

  # timedatectl set-timezone Asia/Tokyo
  ```

## ロケールの初期設定

- デフォルトでは、 `C.UTF-8` ロケールを使用。
- サーバ用途ならこれでも困らないが、一応日本語ロケールもインストールだけしておく。
  ``` shell
  # locale (現在設定の表示)

  # locale-gen ja_JP.UTF-8 (日本語ロケール作成)

  # update-locale LANG=ja_JP.UTF-8 (システムワイドに日本語ロケールを使いたいなら)
  ```

## ネットワークの初期設定

- インストール時は DHCP を使うのが楽。
- しかし、サーバ用途なら IP アドレスも固定するよね。
- Ubuntu 26.04 は netplan を使っている模様なので、そちらで初期設定を入れておく。
- netplan サバイバルガイド
  ``` shell
  # netplan status (現在設定の表示)

  # netplan apply (netplan 設定ファイルを修正した後、反映させるコマンド)
  ```
- `/etc/netplan/00-installer-config.yaml` を書き換えて `netplan apply`。
  ```
  network:
    version: 2
    ethernets:
      enp0s2:
	dhcp4: false
	addresses: [10.0.0.1/24]
	nameservers:
	  addresses: [1.1.1.1, 8.8.8.8]
	routes:
	  - to: default
	    via: 10.0.0.254
  ```

## ufw で自分自身を守る初期設定

- 自ノードを守る(だけ)の ACL を設定。
  - 受信は、自ノードが提供するサーバの待受ポートのみを許可。
  - 送信は、自分発ならすべて許可。
- ufw のコマンドライン
  ``` shell
  # ufw status

  # ufw default deny incoming
  # ufw default allow outgoing
  (# ufw default deny routed)

  # ufw allow 22/tcp comment 'SSH'
  # ufw allow 80/tcp comment 'HTTP'
  # ufw allow 443/tcp comment 'HTTPS'
  (# ufw allow from 10.0.0.0/24 to any port 22 proto tcp)

  # ufw enable

  # ufw status verbose
  # ufw status numbered
  # ufw delete <N>
  ```

## 名前解決関係

- resolv か resolve かとか、もう何がなんだか。
  ``` shell
  # resolvectl status

  # resolvectl query www.yahoo.co.jp
  ```

## sshd の初期設定

- `/etc/ssh/sshd_config.d/50-cloud-init.conf` で初期設定
  ```
  # PasswordAuthentication yes
  PasswordAuthentication no
  PermitRootLogin	no
  Port 22
  ```
- 待受ポートを列挙するには、 `ss -tuln` とか。

## bash の初期設定

- `~/.bash_aliases` にエイリアスを。
  ```
  alias cp="cp -i"
  alias less="lv"
  #alias ls="ls -FG"
  alias lv="lv -c"
  alias more="lv"
  alias mv="mv -i"
  alias rm="rm -i"
  #alias vi="vim"
  #alias view="vim -R"
  ```
- `~/.bash_profile` に環境変数を。
  ```
  #export PS1="[\u@\h \W]\\$ "
  export EDITOR="vi"
  export LANG="ja_JP.UTF-8"
  export LC_MESSAGES="C.UTF-8"
  export LC_TIME="C.UTF-8"
  export PAGER="lv"
  export TMOUT="1200"
  ```
