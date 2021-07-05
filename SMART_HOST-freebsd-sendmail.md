# FreeBSD12R 同梱のsendmailでSMART_HOSTする

[[_TOC_]]

## これは何？

- AWS EC2やGCP GCEでFreeBSD12.2Rなノードを建てた。
- AWS EC2やGCP GCEでは[OP25B](https://www.nic.ad.jp/ja/basics/terms/OP25B.html)が有効になっている。smtps(465/tcp)やsubmission(587/tcp)へのアクセスは可能。(2021/Jul現在)
- FreeBSDのデフォルトのsendmailでは、外部のsmtp(25/tcp)へ接続しようとするので当然に外へのメールを送出できない。
- そこでFreeBSD同梱のsendmailで[SMART_HOST](https://en.wikipedia.org/wiki/Smart_host)を指定して、外部向けのメールをすべてSMART_HOST(のsubmissionポート)へ送るようにしたい。submissionなのでSMTP AUTHを通過する必要がある点に留意する。

## 概要

- まず、FreeBSD同梱のsendmailがsubmissionポートやSMTP AUTHに対応している必要がある。
  [FreeBSD Handbook: 29.9 SMTP AUTH](https://docs.freebsd.org/en/books/handbook/mail/#SMTP-Auth)によれば、ports/security/cyrus-saslをインストールした上でsendmailの再コンパイルが必要であった。
- さらに、/etc/mail/以下のsendmail設定で、SMART_HOSTを指定し、それがsubmissionポートを使うようにMAILERを追加し、SMTP AUTHで用いるID/passwdを指定する必要があった。
- このID/passwdは、SMART_HOST側にも設定が必要である。(面倒な場合は送り側からsmtpsでSMART_HOSTへ接続し、接続元IPアドレスをpostfixでいうmynetworksに入れておくようなことで実現可能かもしれない)

## sendmailをSMTP AUTH対応にする

- [FreeBSD Handbook: 29.9 SMTP AUTH](https://docs.freebsd.org/en/books/handbook/mail/#SMTP-Auth)参照。
- ports/security/cyrus-sasl2をインストールする。
- 自分(送り側のsendmail)がSMTP AUTHする側(サーバ側)になるわけではないので、pwcheck_methodの設定やports/security/cyrus-sasl2-saslauthdのインストールは不要。実際に設定・インストールをしなかった。
- /etc/make.confへの設定追加では、LDFLAGSも必要であった。
  ```
  SENDMAIL_CFLAGS=-I/usr/local/include/sasl -DSASL
  SENDMAIL_LDFLAGS=-L/usr/local/lib -lsasl2 -DSASL
  SENDMALE_LDADD=/usr/local/lib/libsasl2.so
  ```
- sendmailと関連ライブラリの(再)コンパイル
  ```
  # cd /usr/src/lib/libsmutil
  # make cleandir && make obj && make
  # cd /usr/src/lib/libsm
  # make cleandir && make obj && make
  # cd /usr/src/usr.sbin/sendmail
  # make cleandir && make obj && make && make install
  ```

## 送り側で/etc/mail/以下でのsendmail設定
### authinfo
- まず、submissionポートで使うSMTP AUTHのid/passwdなどのデータベースを作る。
  ```
  # touch /etc/mail/authinfo
  # chmod 600 /etc/mail/authinfo
  # vi /etc/mail/authinfo
  AuthInfo:smart.host.fqdn "U:<username>" "P:<passwd>" "M:LOGIN"
  ```
- AuthInfo直後はSMART_HOSTのFQDN
- U:の項はユーザ名
- P:の項はパスワード
- M:の項は認証方法。他にPLAINとかCRAM-MD5などの場合もあるのでSMART_HOST側で受け入れ可能なものを書く。
- authinfoファイルはmakemapでハッシュ化したauthinfo.dbに変換するが、MakefileのSENDMAIL_MAP_SRCの項に追記すればmake一発である(のでそうした)。

### submission用のto587.m4
- 外部のsubmissionポートへメールを送るための(sendmail的)mailerを定義する。
- /usr/share/sendmail/cf/mailer/to587.m4として定義ファイルを作成。
  ```
  Mto587, P=[IPC], F=mDFMuXa8, S=EnvFromSMTP/HdrFromSMTP, R=MasqSMTP, E=\r\n, L=2040, T=DNS/RFC822/SMTP, A=TCP $h 587
  ```
- これで、後述のsendmail.cfなどからto587.m4を読み込んで利用することができる。  

### mcファイル
- 次に、mcファイルの設定変更を行う。
- FreeBSD同梱のsendmailの場合、/etc/mailでmakeすると`<自ノードのFQDN>.mc`と`<自ノードのFQDN>.submit.mc`が生成される。この`<自ノードのFQDN>*.mc`を編集して設定変更し、make installするとsendmail.cfとsubmit.cfとしてインストールされるので、make restartでsendmailプロセスを再起動すると設定変更が反映されることになる。
- `<自ノードのFQDN>.mc`には元々SMART_HOSTや関連設定をdnlでコメントアウトしてあるので、その続きに追記する。
  ```
  TRUST_AUTH_MECH(`GSSAPI DIGEST-MD5 CRAM-MD5 LOGIN PLAIN')dnl
  define(`confAUTH_MECHANISMS', `EXTERNAL GSSAPI DIGEST-MD5 CRAM-MD5 LOGIN PLAIN')dnl
  define(`SMART_HOST', `to587:smart.host.fqdn')dnl
  FEATURE(`authinfo', `hash /etc/mail/authinfo')dnl
  MAILER(`to587')dnl
  ```
- `<自ノードのFQDN>.submit.mc`でも同じ要領で追記するが、FEATUREとMAILERの順序問題があってmake時にエラーになるのでFEATUREを先に定義しておく。
  ```
  dnl If you use IPv6 only, change [127.0.0.1] to [IPv6:0:0:0:0:0:0:0:1]
  TRUST_AUTH_MECH(`GSSAPI DIGEST-MD5 CRAM-MD5 LOGIN PLAIN')dnl
  define(`confAUTH_MECHANISMS', `EXTERNAL GSSAPI DIGEST-MD5 CRAM-MD5 LOGIN PLAIN')dnl
  define(`SMART_HOST', `to587:smart.host.fqdn')dnl
  FEATURE(`authinfo', `hash /etc/mail/authinfo')dnl
  dnl
  FEATURE(`msp', `[127.0.0.1]')dnl
  dnl
  MAILER(`to587')dnl
  ```
- これで`make`すればふたつのmcファイルからそれぞれcfファイルが生成され、`make install`するとcfファイルをsendmail.cfとsubmit.cfとしてインストールする。
- さらに`make restart`すれば新しい設定でsendmailプロセスが動き出す。

## SMART_HOST側

- SMART_HOST側では、submissionポートでSMTP AUTHを受け付けること、また、上で設定したid/passwd他の内容でもってsubmissionポートのSMTP AUTHを通過できることが求められる。
- 単純にUNIXユーザを作るか、まだはDovecotのvirtual.passwdのような機能でvirtualユーザを作成しておけば良い。Dovecotの場合は/usr/local/etc/dovecot/virtual.passwdに以下のように書けば仮想のユーザを作成できる。(dovecotに仮想ユーザを使わせる設定は別途必要)
  ```
  virtual.user@virtual.domain:{CRYPT}$(はなもげら文字列)
  ```
- {CRYPT}及び右側のはなもげらは、`doveadm pw`で生成する。

# ここから下は後で消す。


## どうしてそんな？

- GCP GCEでFreeBSD12Rなノードを建てた。
- GCPはGoogleのクラウド全般を指し、GCEはその中の仮想マシン貸し出しサービスを指す。
- AmazonでいうところのAWSとEC2だと思っている。(2021/Jul/03追記、実はAWS EC2でも同じだった... これだから末法の世はっ(マヤ風)
- GCEではOP25Bが適用されていて、平たく言うと建てたノードからメールを出せない。システム管理上、daily checkのメールは非常に便利なので、これは困る。
- 正しくはegressのSMTP(25/tcp)はブロックされているがSMTPS(465/tcp)とSubmission(587/tcp)は開いているのでそっちを使えば出せないわけではない。
- ところが、FreeBSD同梱のsenmail(/etc/mailに設定ファイルがあるやつ)は、自分発のコネクションをSSL(SMTPS)やTLS(Submission)で包むことが出来ない。（みたい。できるなら是非教えて下さい。）
- そこで、stunnelで自宅サーバのSMTPSポートにSSLトンネルを張っておいて、sendmailからSMART_HOSTでこのトンネルへ投げ込むことを考えた。
- SMART_HOSTはsendmailの機能のひとつで、メール配送で自ノードの外へ送るメールを（通常ならMXやAレコードを参照しながら各相手先ノードのSMTPサーバへ送るところを）全部まとめてSMART_HOSTに指定されたノードへ送るもの。
- 蛇足ながらSMTPSはSSLで包むことを別にすればSMTPと同じ動きで、SMTP-AUTHなしでもメール配送はできる（第三者リレーなんかは設定で止めてあるのが普通で、その場合、自ノードで終端するメールだけ受け取る）。SMTP-AUTHで認証すればSMART_HOSTから見て外部へのメールもリレーする（一般論として）。SubmissionはSMTP-AUTHでの認証なしでは何もできないので、上の構成で作るならSMTPSでなければならないことになる。
- 参考URL
  - [Setup Sendmail Smart Relay in FreeBSD – /var/logs/paulooi.log](https://logs.paulooi.com/)
  - [Configure sendmail as a client for SMTPs - Fedora Project Wiki](https://fedoraproject.org/)
- はっきり言えば、上のふたつの記事を読めば全部書いてある。神のお告げの如き記事であります。感謝。
- 前者はFreeBSD同梱のsendmailについてSMART_HOST設定のやり方を説明しており、FreeBSD特有の扱い(makeとか)も出ている。
- 後者はsendmail一般(というかFedora)について説明していて、特にSMART_HOSTで使用ポートを変更する方法が出ている。
- (2021/Jul/02 追記) amebloから移転した。

## 目指す構成

- このノードのsendmail発のメールをすべてSMART_HOST=127.0.0.1:10025へ送る。
- stunnelで自宅サーバのSMTPSポートから127.0.0.1:10025までトンネルを掘る。SSLで包む部分はstunnelがやってくれるので、sendmailは127.0.0.1:10025でSMTPを喋ればよい。

## stunnel設定

- portsからsecurity/stunnelをインストール。
- /usr/local/etc/stunnelにあるstunnel.conf-sampleを参考にstunnel.confを作成する。
  - `include = /usr/local/etc/stunnel/conf.d`の行を含んでここまでを残し、以下を削除すれば良い。
  - これはこの下にサンプルとしてgmail接続その他のエントリが生きた状態で書いてあるから。
- /usr/local/etc/stunnel/conf.d/ には 00-pid.conf なるファイルがあって、stunnelデーモンのpidファイルは/var/run/stunnel.pidを使ってねと設定してある。
- /usr/local/etc/stunnel/conf.d/に設定ファイルを新設して、そこに127.0.0.1:10025からSMART_HOSTになる側(以下ではexample.org)の465/tcpへのstunnelを張る設定を書く。
    ```
    [fd-smtp]
    client = yes
    accept = 127.0.0.1:10025
    connect = example.org:465
    verifyChain = yes
    CApath = /etc/ssl/certs
    checkHost = flyingdutchman.kawasaki3.org
    OCSPaia = yes
    ```
- /etc/rc.conf.localにstunnel_enable="YES"を書いて、service stunnel startすればトンネルが張れる。
    ```
    stunnel_enable="YES"
    ```
- 起動コマンドは service stunnel start
    ```
    # service stunnel start
    ```

- ~~本当はSSLサーバ証明書の検証をやるべきだが、ちょっとまだ手が回っていない。~~ 一応サーバ側(SMART_HOST側)のSSLサーバ証明書の検証が出来ているようだ。
- 試験としては、まずopensslでstunnel抜きでの接続を確認し、次いでstunnel経由での接続を確認する。どちらも220 example.org ESMTPのようなSMTPバナーが出てくればとりあえずつながっていることがわかる。
    ```
    # openssl s_client -connect example.org:465
    220 example.org ESMTP
    EHLO...
    
    # nc 127.0.0.1 10025
    220 example.org ESMTP
    ```

## FreeBSD特有の/etc/mailでの動き

- FreeBSD同梱のsendmailは、初期状態では自ノード内部からの要求(mailコマンドなど)を受けて自ノード内のユーザメールボックスまたは外部のメールサーバへの転送を行う。外部からのメールを受信することはしない。
- 設定ファイルなどは/etc/mailにあり、makeコマンドを活用して動作する。以下に概要を説明する。
- 直接のsendmailの設定ファイルは/etc/mail下のsendmail.cfとsubmit.cfで、初期状態でも上記の動きをする。
- 設定を変更する場合は、まずmakeすることで自ノードのホスト名を関した一連のファイルを生成する。自ノード名をmynodeとすれば次のような形。
    ```
    # cd /etc/mail
    # make
    cp -f freebsd.mc mynode.mc
    /usr/bin/m4 -D_CF_DIR_=/usr/share/sendmail/cf/   /usr/share/sendmail/cf/m4/cf.m4 mynode.mc > mynode.cf
    cp -f freebsd.submit.mc mynode.submit.mc
    /usr/bin/m4 -D_CF_DIR_=/usr/share/sendmail/cf/   /usr/share/sendmail/cf/m4/cf.m4 mynode.submit.mc > mynode.submit.cf
    ```
- 独自の設定変更はmynode.mcおよびmynode.submit.mcで行い、makeすることでmynode.cfおよびmynode.submit.cfを生成する。
- 生成されたcfファイル群で問題なければmake installすることで本番cfファイル群(sendmail.cf, submit.cf)にコピーする。
    ```
    # make install
    install -m 444 mynode.cf /etc/mail/sendmail.cf
    install -m 444 mynode.submit.cf /etc/mail/submit.cf
    ```
- make restartまたはservice sendmail onerestartすることで新しい設定でsendmailデーモンを稼働させる。
    ```
    # make restart
Restarting: sendmail sendmail-clientmqueue.
    ```

## sendmail設定の修正

- mynode.mcへの修正
    ```
    # diff -u mynode.mc.orig mynode.mc
    --- mynode.mc.orig    2020-10-01 19:19:00.927969000 +0900
    +++ mynode.mc    2020-10-01 19:26:52.062137000 +0900
    @@ -87,6 +87,10 @@

     dnl Dialup users should uncomment and define this appropriately
     dnl define(`SMART_HOST', `your.isp.mail.server')
    +define(`SMART_HOST', `smtp:[127.0.0.1]')dnl
    +define(`RELAY_MAILER_ARGS', `TCP $h 10025')dnl
    +define(`ESMTP_MAILER_ARGS', `TCP $h 10025')dnl
    +dnl FEATURE(`authinfo', `hash /etc/mail/authinfo.db')dnl

     dnl Uncomment the first line to change the location of the default
     dnl /etc/mail/local-host-names and comment out the second line.
    ```
- mynode.submit.mcへの修正
    ```
    # diff -u mynode.submit.mc.orig mynode.submit.mc
    --- mynode.submit.mc.orig    2020-10-01 19:19:00.949538000 +0900
    +++ mynode.submit.mc    2020-10-01 19:28:44.543670000 +0900
    @@ -22,5 +22,8 @@
     define(`confDONT_INIT_GROUPS', `True')dnl
     define(`confBIND_OPTS', `WorkAroundBrokenAAAA')dnl
     dnl
    +define(`SMART_HOST', `smtp:[127.0.0.1]')dnl
    +define(`RELAY_MAILER_ARGS', `TCP $h 10025')dnl
    +define(`ESMTP_MAILER_ARGS', `TCP $h 10025')dnl
     dnl If you use IPv6 only, change [127.0.0.1] to [IPv6:::1]
     FEATURE(`msp', `[127.0.0.1]')dnl
    ```
- ふたつのmcファイルを修正する必要がある点に注意。
- SMART_HOSTの設定は、smtpプロトコルで[127.0.0.1]へすべてのメールをリレーする設定。IPアドレスが[ ]に入っているのでMXを牽いたりせずに直接IPアドレスに接続せよという設定。
- そのままでは25/tcpへ接続にいくので、次の二行で10025番ポートを指定。
- 設定を反映して動作させるために
    ```
    # cd /etc/mail
    # make install restart
    ```
- SMTP-AUTHでログインしたければFEATUREのauthinfoを設定する。上記参考URL参照。ただ、第三者リレーを許可することになるので、スパムをばらまかないように注意すること。ここでは設定しないのでSMART_HOSTが受け取らないメールはフェイルする。

## 第三者転送と見られないために

- ここまでの設定でmynodeで発したメールはすべてSMART_HOSTへ送られる状態。
- なので、SMART_HOST側で受け取るドメイン名に宛てたメールは受け取ってもらえる。
- しかし、mynodeから出ていくメールには、Envelope Fromにmynodeのドメイン名が付くものがあって、これは届かない。例えばこうやって出したメール。
    ```
    mynode$ date | mail -s test someone
    ```
- おまけに、GCEにインストールしたFreeBSD12Rでは、/etc/hostsに自動的にエントリを追加する仕組みがある（使用したイメージの設定によると思われる）ので、こんなエントリが見えることになる。しかもどうやら延々とこの２行がつかされ続けるバグがあるようだ。
    ```
    (/etc/hosts)
    10.xxx.xxx.2 mynode.europe-north1-a.c.s${project_name}.internal mynode  # Added by Google
    169.254.169.254 metadata.google.internal  # Added by Google
    ```
- 対策は、この２行が出現するより前の行に自ノードの名前を書いておくこと。
    ```
    (/etc/hosts)
    10.xxx.xxx.2 mynode.my.domain mynode

    10.xxx.xxx.2 mynode.europe-north1-a.c.s${project_name}.internal mynode  # Added by Google
    169.254.169.254 metadata.google.internal  # Added by Google
    (この後繰り返しこの２行が追加される。助けて）
    ```
- こうすることでmailコマンドで次ノードのユーザ名宛に送ったメールでもEnvelope Fromに@mynode.my.domainが補完されて出ていくことになる。
- これでもなおSMART_HOST側では受け取らない。なぜなら、SMART_HOST側のMTAが@mynode.my.domainを自分が受け取るべきメールだと認識していないから。
- SMART_HOST側はPostfixなので、main.cfのmydestinationに追記すれば良い。

## 感想

- 21世紀も1/5が過ぎたというのにsendmail設定にハマるとは思わなかったが、それはそれで楽しかった。
- stunnelの近端側に25/tcpポートを使えるなら、ひょっとしたらmailertableでルーティングするだけで済むかもしれない。この場合は宛先アドレスのドメイン名ごとに設定を分けることもできるだろう。ifconfig lo0 alias 127.0.0.2/32とかやればできないわけではない。
- PostfixやOpenSMTPdでやるとどうなるかしら。
- sendmailのドキュメントがオンラインでは見当たらない。https://sendmail.org/もどこかへリダイレクトされるし。
- mcファイルの書き方は/etc/mail/mynode.mc冒頭の記述によれば/usr/share/sendmail/cf/READMEか/usr/src/contrib/sendmail/cf/READMEを見よとのこと。
- 今回の構成では、mynode発第三者宛のメールはフェイルする。これを救うにはSMTP-AUTHで認証すれば良いと思うが、その場合にはspamも中継してしまうので要注意。
