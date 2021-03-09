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

## 共通設定



# 
resolv.conf設定確認

名前解決のためのresolv.confもCollins先生が設定済。
172.31.0.2はAWS EC2側が用意しているリゾルバーなので、特に理由がなければこれで十分。
search domainは変更しても良いかもしれない。
# cat /etc/resolv.conf
# Generated by resolvconf
search us-west-2.compute.internal
nameserver 172.31.0.2
(2020/Sep/29追記) search domainを変更するなら/etc/resolvconf.confでこんな感じ。それにしてもこの設定ファイルの名前はかなりびみょー。
search_domains="example.com example.jp"
ntpd設定確認

Collins先生のマシンイメージからインストールしているので、AWS EC2でのntpサーバ169.254.169.123に同期する設定がすでに入っている。
# ntpq -p
remote                 refid               st t when poll reach   delay   offset  jitter
===================================================
*169.254.169.123 10.79.71.196  3 u  537 1024  377 0.306   +0.443   0.079
/etc/aliases

/etc/aliasesでroot宛のメールを適当な受信者へaliasしておく。
root: someone@real.mail.reader
/etc/periodic.conf.local

/etc/periodic.conf.localでシステム管理用の定期起動モノの調整。
# /etc/periodic.conf.local

daily_clean_tmps_enable="YES"
daily_news_expire_enable="NO"
daily_status_ntpd_enable="YES"
daily_status_security_inline="YES"
daily_status_smart_devices="/dev/ada0"

weekly_noid_enable="YES"
weekly_show_badconfig="YES"
weekly_status_security_inline="YES"

monthly_status_security_inline="YES"

security_show_badconfig="YES"
pkgコマンド

よく使うプログラムをインストールするのにpkgコマンドを使う。
# pkg update
# pkg search <package name pattern>
# pkg install <package name>
# pkg upgrade [<package name>]
# pkg delete <package name>
bash

(2020/Sep/29追記)
bash入れるの忘れてました。
# pkg install bash
doas

security/sudoでも良いが、security/doasの方がスパルタン。なんせOpenBSD由来。
sudoだと一回認証されればしばらくの間は認証なしに使えるが、doasでそれができるのはOpenBSDで使ったときだけ（泣）
でも（ネットで見た偉い人のお言葉によると）sudoはちょっと肥大化してきたのでバグ混入も心配しなきゃいけないかも。その点doasはコンパクトやし、あのOpenBSD出身やし。
インストールは
# pkg search doas
doas-6.3                       Simple sudo alternative to run commands as another user
# pkg install doas

# echo "permit persist :wheel" >> /usr/local/etc/doas.conf
lv

moreだとjkで上下するとかできない(よね？)のでついついmisc/lv入れちゃう。
日本語も通るし。
# pkg search lv-4.51
lv-4.51_3                      Powerful Multilingual File Viewer
# pkg install lv
nkf

日本語といえばとりあえずjapanese/nkf
# pkg search ja-nkf
ja-nkf-2.1.4,1                 Network Kanji code conversion Filter
# pkg install ja-nkf
lftp

近頃とんと使わなくなったけれど、anonymous FTPの時に入力少なくて楽なftp/lftp
# pkg search lftp-4.9.1
lftp-4.9.1                     Shell-like command line FTP client
# pkg install lftp-4.9.1
vim

/bin/viでもいいんだけどやっぱり便利なeditors/vim
でもX Window Systemは使う予定もないので、editors/vim-liteで十分だよねと思ったら、なくなっていた。
FreeBSD Forumとか/usr/ports/UPDATINGとか見ると、元々X対応なvimパッケージと、コンソール限定の(ということはX対応を削った)vim-liteがあったが、vim-liteがちっとも「軽く」ないので名称変更してeditors/vim-consoleになったとのこと。
What happened to editors/vim-lite?
Is that what is now called vim-tiny? Or was vim-lite really vim-medium and is now gone? =8^)

forums.freebsd.org


じゃeditors/vim-tinyは何？っていうと、/usr/ports/editors/vim-tiny/pkg-descrの後半に、コンソール限定で、かつvimバイナリだけにした(からヘルプやシンタックスその他ランタイムのファイルを削った)ミニマムインストール、と書いてある。
This is the "tiny" version, which is console-only and contains ONLY the vim
binary. It contains no help files, syntax files, or any other runtime files,
and is designed only for minimal installs. You almost always want the vim
or vim-console package instead.
Xは不要だけどsyntaxは欲しいかなということで、vim-consoleをインストールしておく。
# pkg search vim-console
vim-console-8.2.1110           Improved version of the vi editor (console only)
[root@HarbinCafe0 /usr/home/moto]# pkg install vim-console
git

あと、まあ、いらない人はいらないと思うけど、gitコマンド。
これもX対応を含めて依存関係の大きいdevel/gitを避けてdevel/git-liteにする。
pkg-descrに"This version provides the bare minimum git experience without any bindings."とあるので、bindingsが要るようになったらdevel/gitにしよう。
# pkg search git-lite
git-lite-2.27.0                Distributed source code management tool (lite package)
# pkg install git-lite
(2020/Sep/29追記)gitパッケージがX11関係のライブラリを大量にインストールすると思い込んでましたが違いました。でもまあperl5やpython37にgnupg、あと何故かsubversionも突っ込むので考えどころではあります。
/etc/profile + ~/.bashrc + ~/.bash_profile

基本的な環境変数やaliasを/etc/profileに入れておく。
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

EDITOR=vim;        export EDITOR
PAGER=lv;        export PAGER
LANG=ja_JP.UTF-8;    export LANG
LC_MESSAGES=C;        export LC_MESSAGES
LC_TIME=C;        export LC_TIME
TMOUT=1200;        export TMOUT
PS1="[\u@\h \W]\\$ "     export PS1

MANPATH=${HOME}/local/man:/usr/local/man:/usr/share/man
export MANPATH

PATH=${HOME}/local/sbin:${HOME}/local/bin
PATH=${PATH}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH
これで、ログインユーザとして(bash的には-l付き)bashを起動するとaliasと環境変数が有効になる。
ところが、sshログインでログインシェルのbashを起動したような時に、/etc/profileを読んだあとホームディレクトリの.bash_profile, .bash_login, .profileをこの順に探索して最初に存在したファイルを読み込むので、デフォルトで置かれる.profileを読んでしまう。ここにEDITOR=viとかあるのでこれは避けたい。そこで、空のファイルで良いので~/.bash_profileを作っておくことにした。
$ touch ~/.bash_profile
これでもログインしたあとにコマンドラインからbashを起動するとaliasが抜けるが、bash -lとすることで運用対処。
他のシェルとの兼ね合いとかあったらどうするんだろうね。
まとめ

殴り書きだが一応FreeBSDのノードを建てたらこの辺まではやっておくという備忘録を作った。
書けば書くほどあれはどうするこれはどうすると疑問が膨らむ。
パーティション構成とかファイルシステムのRead Onlyマウント、/boot/loader.confや/etc/sysctl.confの整理もこれからの課題。
おまけ

ちょっとだけ/etc/sysctl.conf.localで調整。
# /etc/sysctl.conf.local

# kern.randompid: Random PID modulus. Special values: 0: disable, 1: choose random value
# kern.randompid: 0
kern.randompid=1

# net.inet.icmp.drop_redirect: Ignore ICMP redirects
# net.inet.icmp.drop_redirect: 0
net.inet.icmp.drop_redirect=1

# net.inet.ip.check_interface: Verify packet arrives on correct interface
# net.inet.ip.check_interface: 0
net.inet.ip.check_interface=1

# net.inet.ip.random_id: Assign random ip_id values
# net.inet.ip.random_id: 0
net.inet.ip.random_id=1

# net.inet.ip.redirect: Enable sending IP redirects
# net.inet.ip.redirect: 1
net.inet.ip.redirect=0

# net.inet.sctp.blackhole: Enable SCTP blackholing, see blackhole(4) for more details
# net.inet.sctp.blackhole: 0
net.inet.sctp.blackhole=2

# net.inet.tcp.blackhole: Do not send RST on segments to closed ports
# net.inet.tcp.blackhole: 0
net.inet.tcp.blackhole=2

# net.inet.tcp.drop_synfin: Drop TCP packets with SYN+FIN set
# net.inet.tcp.drop_synfin: 0
net.inet.tcp.drop_synfin=1

# net.inet.tcp.ecn.enable: TCP ECN support
# net.inet.tcp.ecn.enable: 2
# 0: disabled, 1: enabled for send/recv, 2: enabled for recv
net.inet.tcp.ecn.enable=1

# net.inet.tcp.fast_finwait2_recycle: Recycle closed FIN_WAIT_2 connections faster
# net.inet.tcp.fast_finwait2_recycle: 0
net.inet.tcp.fast_finwait2_recycle=1

# net.inet.tcp.finwait2_timeout: FIN-WAIT2 timeout
# net.inet.tcp.finwait2_timeout: 60000
net.inet.tcp.finwait2_timeout=3000

# net.inet.tcp.icmp_may_rst: Certain ICMP unreachable messages may abort connections in SYN_SENT
# net.inet.tcp.icmp_may_rst: 1
net.inet.tcp.icmp_may_rst=0

# net.inet.tcp.nolocaltimewait: Do not create compressed TCP TIME_WAIT entries for local connections
# net.inet.tcp.nolocaltimewait: 0
net.inet.tcp.nolocaltimewait=1

# net.inet.tcp.per_cpu_timers: run tcp timers on all cpus
# net.inet.tcp.per_cpu_timers: 0
net.inet.tcp.per_cpu_timers=1

# net.inet.tcp.recvbuf_auto: Enable automatic receive buffer sizing
# net.inet.tcp.recvbuf_auto: 1
#net.inet.tcp.recvbuf_auto=1

# net.inet.tcp.rfc1323: Enable rfc1323 (high performance TCP) extensions
# net.inet.tcp.rfc1323: 1
#net.inet.tcp.rfc1323=1

# net.inet.tcp.sack.enable: Enable/Disable TCP SACK support
# net.inet.tcp.sack.enable: 1
#net.inet.tcp.sack.enable=1

# net.inet.tcp.tso: Enable TCP Segmentation Offload
# net.inet.tcp.tso: 1
net.inet.tcp.tso=0

# net.inet.udp.blackhole: Do not send port unreachables for refused connects
# net.inet.udp.blackhole: 0
net.inet.udp.blackhole=1

# security.bsd.hardlink_check_gid: Unprivileged processes cannot create hard links to files owned by other groups
# security.bsd.hardlink_check_gid: 0
security.bsd.hardlink_check_gid=1

# security.bsd.hardlink_check_uid: Unprivileged processes cannot create hard links to files owned by other users
# security.bsd.hardlink_check_uid: 0
security.bsd.hardlink_check_uid=1

# security.bsd.see_jail_proc: Unprivileged processes may see subjects/objects with different jail ids
# security.bsd.see_jail_proc: 1
security.bsd.see_jail_proc=0

# security.bsd.see_other_gids: Unprivileged processes may see subjects/objects with different real gid
# security.bsd.see_other_gids: 1
security.bsd.see_other_gids=0

# security.bsd.see_other_uids: Unprivileged processes may see subjects/objects with different real uid
# security.bsd.see_other_uids: 1
security.bsd.see_other_uids=0

# security.bsd.stack_guard_page: Specifies the number of guard pages for a stack that grows
# security.bsd.stack_guard_page: 1
#security.bsd.stack_guard_page=1

# security.bsd.unprivileged_proc_debug: Unprivileged processes may use process debugging facilities
# security.bsd.unprivileged_proc_debug: 1
security.bsd.unprivileged_proc_debug=0

# security.bsd.unprivileged_read_msgbuf: Unprivileged processes may read the kernel message buffer
# security.bsd.unprivileged_read_msgbuf: 1
security.bsd.unprivileged_read_msgbuf=0
あ、/boot/loader.conf.localもほんの少しだけ。
# /boot/loader.conf.local

accf_dns_load="YES"
