# FreeBSD12 on AWS EC2

[[_TOC_]]

## これは何？

- AWS EC2にFreeBSD 12-RELEASEなノードを建てた時の備忘録。
- 多分自分の役にしか立たない。申し訳ない。
- 以前に[アメブロで書いたやつ](https://ameblo.jp/ypsilondelta/entry-12626790577.html)を更新。

## インスタンス作成

- "AWS Marketplace"でFreeBSDを検索すると色々出てくる。（逆に言うと「クイックスタート」には存在しない）
- Collin Percival先生がいつも良い仕事をしてくれています。感謝！
- 最新のFreeBSD 12を選択。
- EC2インスタンスの利用料金はかかるが、マシンイメージの利用料は無料。
- ステップ２: インスタンスタイプの選択
  - 今回はt3a.smallを使用。
  - 永続的に使う気なので「終了保護の有効化（誤った終了を防止します）」だけはクリックした状態にしておく。
  - /usr/srcや/usr/portsを展開する予定があるのでストレージは30GBにした。
  - パーティションは細かく切りたいのだが、時間の都合で割愛。毎度のことながら後で困るわけだ。
  - あとは適宜サブネット割当とかアクセスポリシー割当とか。
  - SSHの鍵を作ったら死守する。このタイミングを逃すと二度と鍵を取り出す機会はない。既存のものがあれば流用もできる。

## 固定のIPv4アドレス割当

- Elastic IPを作って固定のIPv4アドレスを割り当てた。
- Elastic IPを割り当てないと再起動毎に別の(global) IPv4アドレスで上がってくるのでサーバとしてはちょっと使いにくい。
- FQDNもamazonaws.comの下の長いものになるので、必要なら別に命名しておく。

## 初回アクセス

- 初回アクセスの方法は手元の端末から

  ```shell
  $ ssh -p 22 -i <先程のSSH秘密鍵のファイル> -l ec2-user <先程のElastic IP>
  ```

- これでログインしたら`su`でrootになれるので、すかさずパスワードを変更する。変更後は`su`で`root`のパスワードを要求されるので忘れないこと。

  ```shell
  $ su -
  # passwd root
  # passwd ec2-user
  ```

- `ec2-user`というユーザ名は狙われる可能性があるので適当に変えておく。sshなら一応デフォルトで公開鍵方式でしかログインできないので、大丈夫と思える人は変えなくても良いかもしれない。

  ```shell
  # mv /home/ec2-user /home/<新ユーザ名>
  # pw groupmod -n ec2-user \   # ここでのec2-userはグループ名の方。これを変更する。
      -l <新ユーザ名>             # -lには新グループ名を与える。
                                # 最近はユーザ名とグループ名を同じにするのが流儀らしい。
  # pw usermod -n ec2-user \    # 現ユーザ名のec2-userを指定。これを変更する。
      -l <新ユーザ名> \           # 新ユーザ名を指定。
      -d /home/<新ユーザ名> \     # 新ユーザ名に対応したホームディレクトリを指定。
      -g <新ユーザ名>             # 新グループ名を指定。
  ```

## sshdオプション変更

- デフォルトの22/tcpにはスキャンがたくさんやってくるので、適当なハイポートに逃がす方が気楽。ここでは10022/tcpに移す。

- パスワード認証をさせない、rootログインをさせない、blacklistdを使う、その他の設定を/etc/rc.conf.localで。

  ```shell
  # /etc/rc.conf.local
  sshd_enable="YES"
  sshd_flags="-o ClientAliveCountMax=8 -o ClientAliveInterval=15 -o ListenAddress=0.0.0.0:10022 -o PasswordAuthentication=no -o PermitRootLogin=no -o Protocol=2 -o TCPKeepAlive=yes -o UseDNS=no -o UsePam=no -o X11Forwarding=yes -o KbdInteractiveAuthentication=no -o UseBlackList=yes"
  ```

- sshdプロセス再起動で有効になる。

  ```shell
  # service sshd status
  # service sshd restart
  ```

- 念の為、外からsshでログインできて、su -でroot権限を取れるところまで確認しておくと安心。

## ファイアウォール(ipfw)起動

- 何はともあれ早めにipfwの設定を入れる。

- というのは、失敗するとログインができなくなって（AWS EC2ではコンソールは見えても入力できないので）手も足も出ずインスタンス再作成に追い込まれるから。

- ipfwは暗黙のdefaultルールがdeny allなので、いきなり有効にしては駄目。
    - 2020/Sep/29追記：ipfwのdefault denyをdefault allowにするには、/boot/loader.conf.localで次のtunableを設定すればよい。これが効果を持つのはreboot後である点に注意。

    ```shell
    net.inet.ip.fw.default_to_accept=1
    ```
    - ↑は[FreeBSDワークショップ](https://freebsd-workshop.connpass.com)#67のチャットで教えていただきました。
    
      > FreeBSDワークショップとは
      >
      > FreeBSDワークショップは、FreeBSDの利用や開発に興味のある方向けのイベントです。
      >
      > 参加者が講演を聞くだけのスタイルではなく、ノウハウや日頃の疑問を持ち寄って、参加者の間で意見交換や交流をすることに重点を置いています。 
      >
      > おおよそ月一回のペースで定期的に開催し、毎回、FreeBSDプロジェクトに深く係わる日本人開発者が参加します。
      >
      > 初心者、ヘビーユーザ、開発に興味がある人、誰でも歓迎です。
      >
      > 不満やいつも困っていることなどを、みんなで共有しましょう。
  
- ルールの設定は/etc/ipfw.rulesで

  ```shell
  #!/bin/sh
  IPFWQ="/sbin/ipfw -q"
  
  # clear old configurations.
  $IPFWQ -f flush
  # $IPFWQ -f nat flush
  $IPFWQ table all destroy
  
  # table of good and bad IPs.
  $IPFWQ table T_GOODIP create
  $IPFWQ table T_GOODIP add <trusted ip address>/32 # 要変更。手元アドレスを入れておかないとsshできなくなる。
  $IPFWQ table T_BADIP create
  # $IPFWQ table T_BADIP add <rogue ip address>/32
  
  # loopbacks.
  $IPFWQ add 10 allow ip from any to any via lo0
  $IPFWQ add 11 deny ip from any to 127.0.0.0/8
  $IPFWQ add 12 deny ip from 127.0.0.0/8 to any
  
  # allow good IPs.
  $IPFWQ add 100 allow ip from table\(T_GOODIP\) to me dst-port 10022
  $IPFWQ add 101 deny ip from any to me dst-port 10022
  
  # deny bad IPs.
  $IPFWQ add 60000 deny ip from table\(T_BADIP\) to any
  
  # allow all.
  $IPFWQ add 65000 allow ip from any to any
  
  # DEFAULT DENY added by default.
  # 65535 deny ip from any to any
  ```
  
- ただし、このルールはかなりがばがばなので参考程度にされたし。

- boot時に起動する設定は/etc/rc.conf.localで

    ```shell
    firewall_enable="YES"
    firewall_script="/etc/ipfw.rules"
    ```

- /etc/rc.conf.localにfirewall_enable="YES"があれば、自動でkldload ipfw.koをやってくれるので明示的に記述する必要はないが、どうしてもやるなら/boot/loader.conf.localで

    ```shell
    ipfw_load="YES"
    ```

- 信頼してよい踏み台ノードなどのIPアドレスをT_GOODIPに入れておく。spammerなんかが面倒な時はT_BADIPに入れておく。

    - コマンドラインなら

        ```shell
        # ipfw table T_GOODIP add <踏み台ノードのIPアドレス>/32
        # ipfw table T_GOODIP list
        # ipfw table T_BADIP add <スパマのIPアドレス>/32 # 面倒なら/24くらいでもいいかも。
        # ipfw table T_BADIP list
        ```

- ipfwを有効にする前に、ちょっと落ち着いて上の設定をよく確認するほうがよい。default denyなので、失敗するとsshのログインができないどころか、今コマンドを投入したこのセッションすら叩き落されます。

- ipfwを有効にして、sshでログインできるかどうかを確認する。

    ```shell
    # service ipfw status
    # service ipfw start
    ```

- 有効なipfwルールの確認は

    ```shell
    # ipfw list
    # ipfw table T_GOODIP list
    # ipfw table T_BADIP list
    ```


## blacklistd起動

- ついでにblacklistdも起動。

- これで、sshdで認証失敗を経験したらblacklistdに伝達し、blacklistdでの閾値(個別に設定もできる)を越えたらipfwに拒否ルールを突っ込むという動きになるはず。

- 起動設定は/etc/rc.conf.localで

  ```shell
  blacklistd_enable="YES"
  blacklistd_flags="-f"
  ```

- 細かい動作変更は`/etc/blacklistd.conf`にて。ひょっとしたら自分の作業場所のglobal IPを例外にする(常に許可する)設定や、デフォルトの3回の失敗で24時間拒否するあたりのパラメータを変更する方が良いかもしれない。

- sshdでblacklistdを使うので、blacklistdに対してfirewallとしてはipfwを使えと設定しておく。実は上のsshdの設定には既にblacklistdを使えと書いてある。

  ```shell
  # touch /etc/ipfw-blacklist.rc
  ```
- rebootで自動起動されるが、手動なら

  ```shell
  # service blacklistd status
  # service blacklistd start
  ```

## ホスト名変更

- `/etc/rc.conf.local`で`hostname="new_host_name.example.com"`。

- これはrebootで発効。

- すぐ効かせるなら（といってもプロンプトに出るのは次のシェル起動から）hostnameコマンドで。

  ```shell
  # hostname new_host_name.example.com
  ```

## システムのタイムゾーン

- ユーザ毎の設定で上書きできるけれど、一応システムのタイムゾーンを設定しておく。

  ```shell
  # ls -l /etc/localtime || ln -s /usr/share/zoneinfo/Asia/Tokyo /etc/localtime
  ```

## 初回reboot

- service ipfw startの後もコマンドラインの操作ができていれば大丈夫なはずだが、ipfwの設定を間違ってないことを確認するため、ここで初回reboot。
- もしSSHアクセスができなくなったら、別のVMを建ててこのVMのディスクイメージを/mntあたりにマウントして設定ミスを修正する手段はあるけど、多分、VMを捨てて作り直す方が早い。

# resolv.conf設定確認

- 名前解決のためのresolv.confもCollins先生が設定済。

  ```shell
  $ cat /etc/resolv.conf
  # Generated by resolvconf
  search us-west-2.compute.internal
  nameserver 172.31.0.2
  ```

- 172.31.0.2はAWS EC2側が用意しているリゾルバーなので、特に理由がなければこれで十分。

- search domainは変更しても良いかもしれない。

- (2020/Sep/29追記) search domainを変更するなら/etc/resolvconf.confでこんな感じ。それにしてもこの設定ファイルの名前はかなりびみょー。

  ```shell
  search_domains="example.com example.jp"
  ```

# ntpd設定確認

- Collins先生のマシンイメージからインストールしているので、AWS EC2でのntpサーバ169.254.169.123に同期する設定がすでに入っていて、ntpdも動作している。

  ```shell
  # ntpq -p
       remote           refid      st t when poll reach   delay   offset  jitter
  ==============================================================================
  *169.254.169.123 169.254.169.122  3 u   33   64  377    0.179   +0.029   0.066
  ```

# /etc/aliases

- /etc/aliasesでroot宛のメールを適当な受信者へaliasしておく。

  ```shell
  root: someone@real.mail.reader
  ```

- newaliases(1)を忘れずに。

- 非特権ユーザ(さっきec2-userから名前を変更したやつ)の~/.forwardも手当しておく。

# /etc/periodic.conf.local

- /etc/periodic.conf.localでシステム管理用の定期起動モノの調整。

  ```shell
  # /etc/periodic.conf.local
                                            # ↓ かなりざっくりした説明
  daily_clean_tmps_enable="YES"             # /tmpにある古いファイルを適宜消す。
  daily_news_expire_enable="NO"             # newsシステムのdaily checkをしない。
  daily_status_ntpd_enable="YES"            # ntpdの状態をdaily checkメールに載せる。
  daily_status_security_inline="YES"        # security check結果をdaily checkメールに同梱する。
                                            # NOにすると別々のメールが来る。
  
  weekly_noid_enable="YES"                  # uidが/etc/passwdにないファイルのチェック
  weekly_show_badconfig="YES"               # 設定の不備を指摘(?)
  weekly_status_security_inline="YES"
  
  monthly_status_security_inline="YES"
  
  security_show_badconfig="YES"
  ```

# /etc/ttys

- AWS EC2ではコンソールへの接続は提供されていないが、シングルユーザモードに落とされてもrootパスワードを聞くようにする。

- 他のtty、仮想コンソールやシリアルコンソールでは直接にはrootログインができないようにする。

- 提供されていないためにどうせアクセスできないので仮想コンソールの数を減らしておく。

  ```shell
  # diff -u /etc/ttys.orig /etc/ttys
  --- /etc/ttys.orig	2020-10-23 15:53:05.000000000 +0900
  +++ /etc/ttys	2021-03-11 11:03:37.844948000 +0900
  @@ -27,23 +27,23 @@
   #
   # If console is marked "insecure", then init will ask for the root password
   # when going to single-user mode.
  -console	none				unknown	off secure
  +console	none				unknown	off insecure
   #
  -ttyv0	"/usr/libexec/getty Pc"		xterm	onifexists secure
  +ttyv0	"/usr/libexec/getty Pc"		xterm	onifexists insecure
   # Virtual terminals
  -ttyv1	"/usr/libexec/getty Pc"		xterm	onifexists secure
  -ttyv2	"/usr/libexec/getty Pc"		xterm	onifexists secure
  -ttyv3	"/usr/libexec/getty Pc"		xterm	onifexists secure
  -ttyv4	"/usr/libexec/getty Pc"		xterm	onifexists secure
  -ttyv5	"/usr/libexec/getty Pc"		xterm	onifexists secure
  -ttyv6	"/usr/libexec/getty Pc"		xterm	onifexists secure
  -ttyv7	"/usr/libexec/getty Pc"		xterm	onifexists secure
  +ttyv1	"/usr/libexec/getty Pc"		xterm	off secure
  +ttyv2	"/usr/libexec/getty Pc"		xterm	off secure
  +ttyv3	"/usr/libexec/getty Pc"		xterm	off secure
  +ttyv4	"/usr/libexec/getty Pc"		xterm	off secure
  +ttyv5	"/usr/libexec/getty Pc"		xterm	off secure
  +ttyv6	"/usr/libexec/getty Pc"		xterm	off secure
  +ttyv7	"/usr/libexec/getty Pc"		xterm	off secure
   ttyv8	"/usr/local/bin/xdm -nodaemon"	xterm	off secure
   # Serial terminals
   # The 'dialup' keyword identifies dialin lines to login, fingerd etc.
  -ttyu0	"/usr/libexec/getty 3wire"	vt100	onifconsole secure
  -ttyu1	"/usr/libexec/getty 3wire"	vt100	onifconsole secure
  -ttyu2	"/usr/libexec/getty 3wire"	vt100	onifconsole secure
  -ttyu3	"/usr/libexec/getty 3wire"	vt100	onifconsole secure
  +ttyu0	"/usr/libexec/getty 3wire"	vt100	onifconsole insecure
  +ttyu1	"/usr/libexec/getty 3wire"	vt100	onifconsole insecure
  +ttyu2	"/usr/libexec/getty 3wire"	vt100	onifconsole insecure
  +ttyu3	"/usr/libexec/getty 3wire"	vt100	onifconsole insecure
   # Dumb console
   dcons	"/usr/libexec/getty std.9600"	vt100	off secure
  ```

- 再起動または`kill -HUP 1`で有効になる。

# pkgコマンド

- よく使うプログラムをインストールするのにpkgコマンドを使う。

- まずはupdateから。

  ```shell
  # pkg update
  Updating FreeBSD repository catalogue...
  Fetching packagesite.txz: 100%    6 MiB   6.5MB/s    00:01    
  Processing entries: 100%
  FreeBSD repository update completed. 30177 packages processed.
  All repositories are up to date.
  ```

- その他の使い方はざっくりこんな感じ。

  ```shell
  # pkg update                            リポジトリから最新カタログを貰ってくる。
  # pkg search <package name pattern>     インストールしたいソフトを名前で探す。
  # pkg install <package name>            インストールする。
  # pkg upgrade [<package name>]          インストール済のものを更新する。
  # pkg delete <package name>             不要になったものを削除する。
  # pkg info [<package name>]             インストール済パッケージの情報を得る。
  ```

# shells/bashインストール

- (2020/Sep/29追記) bash入れるの忘れてました。

- 今回はbash-completionも入れてみる。

  ```shell
  # pkg info bash 
  pkg: No package(s) matching bash
  
  # pkg search bash 
  bash-5.1.4                     GNU Project's Bourne Again SHell
  bash-completion-2.11,2         Programmable completion library for Bash
  bash-static-5.1.4              GNU Project's Bourne Again SHell
  bashtop-0.9.25_1               Linux/OSX/FreeBSD resource monitor
  checkbashisms-2.19.6           Check for the presence of bashisms
  erlang-mochiweb-basho-2.9.0p2  Erlang library for building lightweight HTTP servers (Basho fork)
  mybashburn-1.0.2_4             Ncurses CD burning bash script
  p5-Bash-Completion-0.008_2     Extensible system to provide bash completion
  p5-Term-Bash-Completion-Generator-0.02.8_2 Generate bash completion scripts
  switchBashZsh-1.1              Portable shell setup for Bash/Zsh across FreeBSD/Linux/Cygwin
  
  # pkg install bash bash-completion
  Updating FreeBSD repository catalogue...
  FreeBSD repository is up to date.
  All repositories are up to date.
  The following 2 package(s) will be affected (of 0 checked):
  
  New packages to be INSTALLED:
  	bash: 5.1.4
  	bash-completion: 2.11,2
  
  Number of packages to be installed: 2
  
  The process will require 9 MiB more space.
  2 MiB to be downloaded.
  
  Proceed with this action? [y/N]: y
  [1/2] Fetching bash-5.1.4.txz: 100%    1 MiB   1.5MB/s    00:01    
  [2/2] Fetching bash-completion-2.11,2.txz: 100%  228 KiB 233.4kB/s    00:01    
  Checking integrity... done (0 conflicting)
  [1/2] Installing bash-5.1.4...
  [1/2] Extracting bash-5.1.4: 100%
  [2/2] Installing bash-completion-2.11,2...
  [2/2] Extracting bash-completion-2.11,2: 100%
  =====
  Message from bash-completion-2.11,2:
  
  --
  To enable the bash completion library, add the following to
  your .bashrc file:
  
  [[ $PS1 && -f /usr/local/share/bash-completion/bash_completion.sh ]] && \
  	source /usr/local/share/bash-completion/bash_completion.sh
  
  See /usr/local/share/doc/bash-completion/README.md for more information.
  ```

- rootのログインシェルはデフォルトの/bin/shのままにしておくが、一般ユーザの方はbashに変える。

- 当該一般ユーザのコマンドラインから

  ```shell
  $ chsh -s /usr/local/bin/bash
  Password: ************
  chsh: user information updated
  ```

  - シェルへのfull pathが/etc/shellsに存在しない場合はchshコマンドがエラーになるので、タイポしても安全。
  - bashのfull pathはpkgでインストールした時に入れてくれている。野良コンパイルした場合などは手動で編集(追加)する必要がある。

- **または**、rootからやるなら

  ```shell
  # pw usermod <username> -s /usr/local/bin/bash
  ```

  - pwでやる場合は、full pathをタイポしても拒否してくれないので、rootアカウントをログイン状態に保持したままで、sshログインできることを確認すべき。

# security/sudoまたはsecurity/doas

- security/sudoでも良いが、security/doasの方がスパルタン。なんせOpenBSD由来。

- sudoだと一回認証されればしばらくの間は認証なしに使えるが、doasでそれができるのはOpenBSDで使ったときだけ（泣）

- でも（ネットで見た偉い人のお言葉によると）sudoはちょっと肥大化してきたのでバグ混入も心配しなきゃいけないかも。その点doasはコンパクトやし、あのOpenBSD出身やし。この間はsudoで脆弱性が見つかってたし。

- インストールは

  ```shell
  # pkg install doas
  Updating FreeBSD repository catalogue...
  FreeBSD repository is up to date.
  All repositories are up to date.
  The following 1 package(s) will be affected (of 0 checked):
  
  New packages to be INSTALLED:
  	doas: 6.3p2
  
  Number of packages to be installed: 1
  
  18 KiB to be downloaded.
  
  Proceed with this action? [y/N]: y
  [1/1] Fetching doas-6.3p2.txz: 100%   18 KiB  18.0kB/s    00:01    
  Checking integrity... done (0 conflicting)
  [1/1] Installing doas-6.3p2...
  [1/1] Extracting doas-6.3p2: 100%
  =====
  Message from doas-6.3p2:
  
  --
  To use doas,
  
  /usr/local/etc/doas.conf
  
  must be created. Refer to doas.conf(5) for further details and/or follow
  /usr/local/etc/doas.conf.sample as an example.
  
  Note: In order to be able to run most desktop (GUI) applications, the user
  needs to have the keepenv keyword specified. If keepenv is not specified then
  key elements, like the user's $HOME variable, will be reset and cause the GUI
  application to crash.
  
  Users who only need to run command line applications can usually get away
  without keepenv.
  
  When in doubt, try to avoid using keepenv as it is less secure to have
  environment variables passed to privileged users.
  ```

- /usr/local/etc/doas.confを設定する。/usr/local/etc/doas.conf.sampleがあるのでコピーして適宜編集。

  ```shell
  # diff -u doas.conf.sample doas.conf
  --- doas.conf.sample	2021-02-28 07:13:32.000000000 +0900
  +++ doas.conf	2021-03-10 11:56:18.205366000 +0900
  @@ -6,13 +6,13 @@
   permit :wheel
   
   # Permit user alice to run commands a root user.
  -permit alice as root
  +### permit alice as root
   
   # Permit user bob to run programs as root, maintaining
   # envrionment variables. Useful for GUI applications.
  -permit keepenv bob as root
  +### permit keepenv bob as root
   
   # Permit user cindy to run only the pkg package manager as root
   # to perform package updates and upgrades.
  -permit cindy as root cmd pkg update
  -permit cindy as root cmd pkg upgrade
  +### permit cindy as root cmd pkg update
  +### permit cindy as root cmd pkg upgrade
  
  ```

  - root権限を持つ必要のある人はwheelグループに入れることにして、`permit :wheel`の行で設定。
  - alice, bob, cindyの行は設定の書き方の例だと思うが、万一この名前のユーザがいたらどうするんだろね。というわけでコメントアウト。

# misc/lv

- moreだとjkで上下するとかできない(よね？)のでついついmisc/lv入れちゃう。日本語も通るし。

  ```shell
  # pkg install lv
  Updating FreeBSD repository catalogue...
  FreeBSD repository is up to date.
  All repositories are up to date.
  The following 1 package(s) will be affected (of 0 checked):
  
  New packages to be INSTALLED:
  	lv: 4.51.20200728
  
  Number of packages to be installed: 1
  
  324 KiB to be downloaded.
  
  Proceed with this action? [y/N]: y
  [1/1] Fetching lv-4.51.20200728.txz: 100%  324 KiB 331.7kB/s    00:01    
  Checking integrity... done (0 conflicting)
  [1/1] Installing lv-4.51.20200728...
  [1/1] Extracting lv-4.51.20200728: 100%
  ```

# japanese/nkf

- 日本語文字コードや改行文字の変換など。

  ```shell
  # pkg install ja-nkf
  Updating FreeBSD repository catalogue...
  FreeBSD repository is up to date.
  All repositories are up to date.
  The following 1 package(s) will be affected (of 0 checked):
  
  New packages to be INSTALLED:
  	ja-nkf: 2.1.4,1
  
  Number of packages to be installed: 1
  
  150 KiB to be downloaded.
  
  Proceed with this action? [y/N]: y
  [1/1] Fetching ja-nkf-2.1.4,1.txz: 100%  150 KiB 154.1kB/s    00:01    
  Checking integrity... done (0 conflicting)
  [1/1] Installing ja-nkf-2.1.4,1...
  [1/1] Extracting ja-nkf-2.1.4,1: 100%
  ```

# ftp/lftp

- 近頃とんと使わなくなったけれど、anonymous FTPの時に入力少なくて楽なftp/lftp

  ```shell
  # pkg install lftp
  Updating FreeBSD repository catalogue...
  FreeBSD repository is up to date.
  All repositories are up to date.
  The following 4 package(s) will be affected (of 0 checked):
  
  New packages to be INSTALLED:
  	expat: 2.2.10
  	lftp: 4.9.2
  	libidn2: 2.3.0_1
  	libunistring: 0.9.10_1
  
  Number of packages to be installed: 4
  
  The process will require 8 MiB more space.
  2 MiB to be downloaded.
  
  Proceed with this action? [y/N]: y
  [1/4] Fetching lftp-4.9.2.txz: 100%  920 KiB 942.2kB/s    00:01    
  [2/4] Fetching expat-2.2.10.txz: 100%  124 KiB 126.8kB/s    00:01    
  [3/4] Fetching libidn2-2.3.0_1.txz: 100%  110 KiB 113.1kB/s    00:01    
  [4/4] Fetching libunistring-0.9.10_1.txz: 100%  513 KiB 525.6kB/s    00:01    
  Checking integrity... done (0 conflicting)
  [1/4] Installing libunistring-0.9.10_1...
  [1/4] Extracting libunistring-0.9.10_1: 100%
  [2/4] Installing expat-2.2.10...
  [2/4] Extracting expat-2.2.10: 100%
  [3/4] Installing libidn2-2.3.0_1...
  [3/4] Extracting libidn2-2.3.0_1: 100%
  [4/4] Installing lftp-4.9.2...
  [4/4] Extracting lftp-4.9.2: 100%
  ```

# editors/vim-console

- /bin/viでもいいんだけどやっぱり便利なvimがいいねということで入れておく。

- 2021/Mar/10現在、portsには下の３つがあって、いずれかを選んでインストールすれば良い。

  - editors/vim無印はX Window Systemにも対応したフルセット。
  - editors/vim-consoleはX Window System対応を抜いたもの。
  - editors/vim–tinyはさらにヘルプや各プログラム言語対応の文法ファイルなども抜いてサイズを抑えたもの。
  - [FreeBSD Forum](https://forums.freebsd.org/threads/what-happened-to-editors-vim-lite.64495/)とか/usr/ports/UPDATINGとか見ると、元々X対応なvimパッケージと、コンソール限定の(ということはX対応を削った)vim-liteがあったが、vim-liteがちっとも「軽く」ないので名称変更してeditors/vim-consoleになったとのこと。

- Xは不要だけどsyntaxは欲しいかなということで、vim-consoleをインストールしておく。

  ```shell
  # pkg install vim-console
  Updating FreeBSD repository catalogue...
  FreeBSD repository is up to date.
  All repositories are up to date.
  The following 1 package(s) will be affected (of 0 checked):
  
  New packages to be INSTALLED:
  	vim-console: 8.2.2263
  
  Number of packages to be installed: 1
  
  The process will require 26 MiB more space.
  6 MiB to be downloaded.
  
  Proceed with this action? [y/N]: y
  [1/1] Fetching vim-console-8.2.2263.txz: 100%    6 MiB   6.3MB/s    00:01    
  Checking integrity... done (0 conflicting)
  [1/1] Installing vim-console-8.2.2263...
  [1/1] Extracting vim-console-8.2.2263: 100%
  ```

- とりあえずこれを~/.vimrcに入れておかねば僕は生きていけない。

  ```shell
  # ~/.vimrc
  set mouse-=a
  set syntax=on
  ```

  

# git

- あと、まあ、いらない人はいらないと思うけど、gitコマンド。

- これもX対応を含めて依存関係の大きいdevel/gitを避けてdevel/git-liteにする。

- pkg-descrに"This version provides the bare minimum git experience without any bindings."とあるので、bindingsが要るようになったらdevel/gitにしよう。

  ```shell
  # pkg install git-lite
  Updating FreeBSD repository catalogue...
  FreeBSD repository is up to date.
  All repositories are up to date.
  The following 4 package(s) will be affected (of 0 checked):
  
  New packages to be INSTALLED:
  	curl: 7.74.0
  	git-lite: 2.30.1
  	libnghttp2: 1.42.0
  	pcre: 8.44
  
  Number of packages to be installed: 4
  
  The process will require 37 MiB more space.
  7 MiB to be downloaded.
  
  Proceed with this action? [y/N]: y
  [1/4] Fetching git-lite-2.30.1.txz: 100%    5 MiB   4.7MB/s    00:01    
  [2/4] Fetching curl-7.74.0.txz: 100%    1 MiB   1.4MB/s    00:01    
  [3/4] Fetching libnghttp2-1.42.0.txz: 100%  123 KiB 125.7kB/s    00:01    
  [4/4] Fetching pcre-8.44.txz: 100%    1 MiB   1.3MB/s    00:01    
  Checking integrity... done (0 conflicting)
  [1/4] Installing libnghttp2-1.42.0...
  [1/4] Extracting libnghttp2-1.42.0: 100%
  [2/4] Installing curl-7.74.0...
  [2/4] Extracting curl-7.74.0: 100%
  [3/4] Installing pcre-8.44...
  [3/4] Extracting pcre-8.44: 100%
  [4/4] Installing git-lite-2.30.1...
  ===> Creating groups.
  Creating group 'git_daemon' with gid '964'.
  ===> Creating users
  Creating user 'git_daemon' with uid '964'.
  [4/4] Extracting git-lite-2.30.1: 100%
  =====
  Message from git-lite-2.30.1:
  
  --
  If you installed the GITWEB option please follow these instructions:
  
  In the directory /usr/local/share/examples/git/gitweb you can find all files to
  make gitweb work as a public repository on the web.
  
  All you have to do to make gitweb work is:
  1) Please be sure you're able to execute CGI scripts in
     /usr/local/share/examples/git/gitweb.
  2) Set the GITWEB_CONFIG variable in your webserver's config to
     /usr/local/etc/git/gitweb.conf. This variable is passed to gitweb.cgi.
  3) Restart server.
  
  
  If you installed the CONTRIB option please note that the scripts are
  installed in /usr/local/share/git-core/contrib. Some of them require
  other ports to be installed (perl, python, etc), which you may need to
  install manually.
  ```

- (2020/Sep/29追記)gitパッケージがX11関係のライブラリを大量にインストールすると思い込んでましたが違いました。でもまあperl5やpython37にgnupg、あと何故かsubversionも突っ込むので考えどころではあります。

# /etc/profile + ~/.bashrc + ~/.bash_profile

- 基本的な環境変数やaliasを/usr/local/etc/profileに入れておく。

  ```shell
  # /usr/local/etc/profileに追加
  alias cp='cp -i'
  alias ftp='lftp'
  alias less='lv'
  alias ls='ls -FG'
  alias more='lv'
  alias mv='mv -i'
  alias rm='rm -i'
  alias sudo=doas
  alias tac='tail -r'
  alias vi='vim'
  alias view='vim -R'
  
  EDITOR=vim;          export EDITOR
  PAGER=lv;            export PAGER
  LANG=ja_JP.UTF-8;    export LANG
  LC_MESSAGES=C;       export LC_MESSAGES
  LC_TIME=C;           export LC_TIME
  TMOUT=1200;          export TMOUT
  PS1="[\u@\h \W]\\$ " export PS1
  TZ=JST-9;            export TZ
  
  MANPATH=${HOME}/local/man:/usr/local/man:/usr/share/man
  export MANPATH
  
  PATH=${HOME}/local/sbin:${HOME}/local/bin
  PATH=${PATH}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
  export PATH
  ```

- 以前は/etc/profileに書いていたが、2021/Mar/10現在のshells/bashでは/usr/local/etc/profileを見るのであって/etc/profileを見ないという動作になっている。

- これで、ログインユーザとして(bash的には-l付き)bashを起動するとaliasと環境変数が有効になる。

- ところが、sshログインでログインシェルのbashを起動したような時に、/etc/profileを読んだあとホームディレクトリの.bash_profile, .bash_login, .profileをこの順に探索して最初に存在したファイルを読み込むので、デフォルトで置かれる.profileを読んでしまう。ここにEDITOR=viとかあるのでこれは避けたい。そこで、空のファイルで良いので~/.bash_profileを作っておくことにした。

  ```shell
  $ touch ~/.bash_profile
  ```

- これでもログインしたあとにコマンドラインからbashを起動するとaliasが抜けるが、bash -lとすることで運用対処。

- 他のシェルとの兼ね合いとかあったらどうするんだろうね。

# まとめ

- 殴り書きだが一応FreeBSDのノードを建てたらこの辺まではやっておくという備忘録を作った。
- 書けば書くほどあれはどうするこれはどうすると疑問が膨らむ。
- パーティション構成とかファイルシステムのRead Onlyマウント、/boot/loader.confや/etc/sysctl.confの整理もこれからの課題。

# おまけ

### ちょっとだけ/etc/sysctl.conf.localで調整。

- これは何？とか訊いてはいけませんです。

  ```shell
  # /etc/sysctl.conf.local
  
  dev.igb.0.fc=0	# was 3: full flow control
  dev.igb.0.iflib.rx_budget=65535	# was 0: 16 frames
  dev.igb.1.fc=0	# was 3: full flow control
  dev.igb.1.iflib.rx_budget=65535	# was 0: 16 frames
  kern.ipc.maxsockbuf=4194304	# was 2097152. 4194304 for 2Gbps
  kern.ipc.shm_use_phys=1	# was 0
  kern.ipc.shmall=4194304		 # was 131072(128kpages), now 4Mpages
  kern.ipc.shmmax=17179869184	# was 536870912(512MB), now 16GB
  kern.msgbuf_show_timestamp=1	# was 0
  kern.random.fortuna.minpoolsize=128	# was 64
  kern.random.harvest.mask=65887	# was 66047
  kern.randompid=1
  ### net.bpf.optimize_writers=1	# was 0
  net.inet.icmp.drop_redirect=1	# was 0
  net.inet.ip.check_interface=1	# was 0
  net.inet.ip.maxfragpackets=7810	# was 3905
  net.inet.ip.maxfragsperpacket=32	# was 16
  net.inet.ip.portrange.first=32768	# was 10000
  net.inet.ip.portrange.randomcps=100	# was 10
  net.inet.ip.portrange.randomtime=10	# was 45 sec
  net.inet.ip.random_id=1	# was 0
  net.inet.ip.redirect=0	# was 1
  net.inet.sctp.blackhole=2	# was 0
  net.inet.tcp.abc_l_var=2	# was 2
  net.inet.tcp.blackhole=2	# was 0
  net.inet.tcp.drop_synfin=1	# was 0
  net.inet.tcp.fast_finwait2_recycle=1	# was 0
  net.inet.tcp.finwait2_timeout=10000	# was 60000 (60sec)
  net.inet.tcp.icmp_may_rst=0	# was 1
  net.inet.tcp.initcwnd_segments=20	# was 10
  net.inet.tcp.isn_reseed_interval=3700	# was 0
  net.inet.tcp.keepcnt=2	# was 8
  net.inet.tcp.keepidle=62000	# was 7200000 (7200sec)
  net.inet.tcp.keepinit=5000	# was 75000 (75sec)
  net.inet.tcp.minmss=536	# was 216
  net.inet.tcp.msl=3000		# was 30000 (30sec)
  net.inet.tcp.mssdflt=1420	# was 536
  net.inet.tcp.path_mtu_discovery=1	# disable for mtu=1500 as most hosts drop ICMP type 3 packets, but keep enabled for mtu=9000 (default 1)
  net.inet.tcp.recvbuf_inc=32768     # (default 16384)
  net.inet.tcp.recvbuf_max=8388608  # (default 2097152)
  net.inet.tcp.recvbuf_auto=1
  net.inet.tcp.rfc1323=1
  ### net.inet.tcp.rfc6675_pipe=1	# was 0
  net.inet.tcp.sendbuf_inc=16384     # (default 8192)
  net.inet.tcp.sendbuf_max=4194304  # (default 2097152)
  ### net.inet.tcp.syncache.rexmtlimit=0	# was 3
  ### net.inet.tcp.syncookies=0	# was 1
  net.inet.tcp.tso=0	# was 1
  net.inet.udp.blackhole=1          # drop udp packets destined for closed sockets (default 0)
  security.bsd.hardlink_check_gid=1 # unprivileged processes may not create hard links to files owned by other groups, DISABLE for mailman (default 0)
  security.bsd.hardlink_check_uid=1 # unprivileged processes may not create hard links to files owned by other users,  DISABLE for mailman (default 0)
  security.bsd.see_jail_proc=0
  security.bsd.see_other_gids=0
  security.bsd.see_other_gids=0     # groups only see their own processes. root can see all (default 1)
  security.bsd.see_other_uids=0
  security.bsd.see_other_uids=0     # users only see their own processes. root can see all (default 1)
  security.bsd.stack_guard_page=1   # insert a stack guard page ahead of growable segments, stack smashing protection (SSP) (default 0)
  security.bsd.unprivileged_proc_debug=0
  security.bsd.unprivileged_proc_debug=0 # unprivileged processes may not use process debugging (default 1)
  security.bsd.unprivileged_read_msgbuf=0
  security.bsd.unprivileged_read_msgbuf=0 # unprivileged processes may not read the kernel message buffer (default 1)
  vfs.zfs.min_auto_ashift=12
  ```

  ### /boot/loader.conf.localもほんの少しだけ。

  ```shell
  # /boot/loader.conf.local
  
  #boot_verbose="-v"
  
  kern.geom.label.disk_ident.enable="0"
  kern.geom.label.gptid.enable="0"
  # zfs_load="YES" # to avoid fixing RAIDZ in single user mode prohibit to login.
  # geom_mirror_load="YES"
  
  ### Serial Console
  # boot_multicons="YES"
  # console="comconsole,efi"
  # comconsole_port="1016"
  # comconsole_speed="9600"
  
  ### fast booting.
  autoboot_delay="-1"
  beastie_disable="YES"
  
  ### ACCF
  accf_data_load="YES"
  accf_dns_load="YES"
  accf_http_load="YES"
  
  ### AESNI
  aesni_load="YES"
  
  ### TCP Congestion Control.
  cc_cubic_load="YES"
  cc_htcp_load="NO"
  cc_cdg_load="NO"
  cc_dctcp_load="NO"
  
  ### kernel module.
  if_ena_load="YES"     # for AWS EC2.
  ipfw_load="YES"
  mac_ntpd_load="YES"
  
  net.inet.tcp.syncache.bucketlimit="64"  # was 30
  net.inet.tcp.syncache.cachelimit="30728"        # was 15364
  net.inet.tcp.syncache.hashsize="1024"   # was 512
  net.inet.tcp.tcbhashsize="1048576"        # was 524288
  net.link.ifqmaxlen="2048"       # was 50
  #vm.swap_enabled=0
  
  ### https://calomel.org/freebsd_network_tuning.html
  # vfs.zfs.dirty_data_max_max="12884901888"      # default=4294967296 (4GB)
  net.inet.tcp.hostcache.cachelimit=30720           # was 15360
  net.inet.tcp.soreceive_stream=1               # was 0
  net.isr.maxthreads="-1"  # (default 1, single threaded)
  net.isr.bindthreads="1"  # (default 0, runs randomly on any one cpu core)
  net.inet.ip.fw.dyn_parent_max: 4096
  net.inet.ip.fw.dyn_max: 16384
  net.inet.ip.fw.default_to_accept: 0
  
  # for jail
  nullfs_load="YES"
  ```

