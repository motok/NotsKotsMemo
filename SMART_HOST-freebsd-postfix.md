# FreeBSD12.2p7 AWS SESをpostfixのSMART_HOSTとして使う

[[_TOC_]]

## これは何？

- AWS EC2EでFreeBSD12.2R(今はp7)なノードを建てた。
- AWS EC2では[OP25B](https://www.nic.ad.jp/ja/basics/terms/OP25B.html)
  が有効になっている。smtps(465/tcp)やsubmission(587/tcp)へのアクセス
  は可能。(2021/Oct現在)
- FreeBSDのデフォルトのsendmailでは、外部のsmtp(25/tcp)へ接続しようと
  するので当然に外へのメールを送出できない。
- そこでFreeBSD同梱のsendmailで
  [SMART_HOST](https://en.wikipedia.org/wiki/Smart_host)を指定して、外
  部向けのメールをすべてSMART_HOST(のsubmissionポート)へ送るようにした
  い。submissionなのでSMTP AUTHを通過する必要がある点に留意する。
- そして、SMART_HOSTとしてAWS SES (Simple Email Service)のSMTPサーバを
  用いることにする。これはSMTPS (465/tcp)とSubmissions (587/tcp)で待ち
  受けている。(AWSのドキュメントの一部にはSMTP (25/tcp)でも待ち受ける
  ように書いてあるが、今回試したところそもそもTCPが繋がらないのでダメ)
- OS同梱のsendmailをSASL対応にするには/usr/src下で再コンパイルが必要だ
  が、そこまでするくらいならportsのmail/postfix-saslをインストールする
  方が楽なのでpostfixにする。-sasl付きなのはAWS SESのSMTPサーバの認証
  を通過するため。
- SESに限らず一般にAWSの使い方についてはさまざまな情報がWebや書籍に
  公開されているのでそちらを参照のこと。
  今回僕は
  [AWSではじめるインフラ構築入門](https://www.seshop.com/product/detail/23455)
  で基本的なところを学んだ。
  AWS的手順はAWSのドキュメントにあるが、それが何をしたくてやっているの
  かの「そのココロ」が知りたい方におすすめの良書である。
- 2021/Oct/21ごろ書いた。

## AWS SESに送信側ドメイン名をverifyさせる。

- まず、AWSコンソールから送信側のドメイン名をverifyする必要がある。
- Amazon SESのclassicコンソールでは`Identity Management / Domains`、
  newコンソールでは`Configuration / Verified Identities`で
  `Create identity`をするときの`Identity type`を`Domain`にするってこと
  になると思う。
- AWS EC2のVMのホスト名に使うドメイン名(ここではexample.jp)を
  verifyすることにして入力して進んでいくと、
  example.jpの権威DNSサーバでいくつかのリソースレコードを設定せよ
  と言われる。
  ここでメモしておく必要のあるデータはこんな感じ。
  適当に書き換えているのであくまで例示である。
  ```
  [Domain Identities]
  example.jp

  [Domain Verification Record]
  _amazonses.example.jp TXT <MIME64っぽい長めの文字列>

  [DKIM Record Set]
  <nonceっぽい文字列１>._domainkey.example.jp CNAME <nonceっぽい文字列1>.dkim.amazonses.com
  <nonceっぽい文字列２>._domainkey.example.jp CNAME <nonceっぽい文字列２>.dkim.amazonses.com
  [Email Receiving Record]
  example.jp MX 10 inbound-smtp.cc-direction-1.amazonaws.com
```
    - Domain Identitesは今verifyさせようとしているドメイン名。
    - Domain Verification Recordは、AWSが`_amazonses.example.jp`を
      `TXT`で引いて、本当に僕がこのドメイン名を制御しているかを確認す
      るためのものだと思われる。当然設定した。
    - DKIM Record SetはAWS SESがSMART_HOSTとしてexample.jp発のメールを
	  送る時に、DKIMの設定をしておきたい時はこれを使う。
	  今時なら入れておいた方がよさそうなので設定した。
    - Email Receiving Recordは、example.jpでメールを受信したい時には
	  必須。僕は送信できればそれで良いので設定しなかった。

- 上記のRRをexample.jpの権威DNSサーバに設定して数分待つと、
  送信側のドメイン名がAWSによってverify済みになった。(AWS SESコンソー
  ルで確認)
- example.jpがverifyされることで、AWS SESのSMTPサーバ(プログラムを使って
  も同じ)でメール送信をする時に送信側のメールアドレスがこのドメイン名
  の傘下にあればOKになる。
  (別途受信側のメールアドレスも検証されるのでこれだけではメール送信で
  きない)
  foo@example.jp発で良いのは当然として、サブドメイン付きの
  bar@hoge.example.jp発でも良いみたい。

## AWSに受信側のメールアドレスをverifyさせる。

- AWS SESコンソールのEmail Addressesから受信側メールアドレスを投入する
  と、当該メールアドレスに認証リンクを書いたメールが飛ぶので、そのリン
  クを踏む。
  すると、受信側メールアドレスをAWSにverifyさせることができる。
- これで、AWS SESのSMTPサーバを使ってメールを送るときの、
  受信側のメールアドレスとして(AWS側によって)認められるようになる。
- 受信側メールアドレスが複数必要なら複数登録する必要がある。
- 送信側ドメイン名と受信側メールアドレスのverifyができたので、
  AWS側のSMTPサーバ(:465)を利用してメールを送ることができるように
  なったわけである。
- プログラムから送るだけならこれでメール送信が可能。
  ただし、まだsandbox内なので通数制限などがある。

## AWS SES側SMTPサーバのSASL認証を通過するためのアカウント作成

- (プログラムからではなく)自ノードのSMTPサーバから、AWS SESのSMTPサーバを
  SMART_HOST(といっても登録済み受信メールアドレス宛でなければ
  送れないが)として使うために、自ノードのSMTPサーバの設定を行う。
- そのためには、自ノードのSMTPサーバがAWS SES側のSMTPサーバに
  対してSASL認証を通過できるようになる必要がある。
- その第一段階として、SASL認証に用いるIAMユーザを作成する。
  SMTPサーバの設定は次節。
- AWS SESコンソール(classic)の`SMTP Settings`から
  `Create My SMTP Credentials`ボタンを押してIAMユーザを
  作成する。
  このページにAWS SES側SMTPサーバの諸元が出ているのでメモ
  しておくこと。
  ```
  Server Name:   email-smtp.cc-direction-1.amazonaws.com
  Port:          25, 465 or 587
  Use TLS:       Yes

  IAM User Name: <自分でつけたIAMユーザ名>
  Smtp Username: <ユーザ名として使う文字列が与えられる>
  Smtp Password: <パスワードとして使う文字列が与えられる>
  ```
- 送信側のドメイン名と受信側のメールアドレスを登録した上で、
  この認証情報を使って与えられたAWS SES側SMTPサーバで
  認証を通過すると、メール送信ができるはずである。

## 自ノードのSMTPサーバとして/etc/mailのsendmailを使う(失敗)

- /etc/mailでsendmailの設定変更でなんとかしてメール送信ができるように
  しようとしたが、それには/usr/src/usr.sbin/sendmailで再コンパイルが
  必要になることがわかった。
  そっちで頑張るよりもportsのmail/postfix\_saslを入れる方が楽なので
  今回はpostfix\_saslをs使うことにした。
- sendmailでの設定方法は
  [Amazon SESとSendmailの統合](https://docs.aws.amazon.com/ja_jp/ses/latest/DeveloperGuide/send-email-sendmail.html)
  に説明があるが、OS同梱のsendmailにはSASL対応が入っていないので
  この設定をしても相変わらずMXの先のメールホストへ接続を試みて
  (OP25Bに引っかかって)いた。

## 自ノードのSMTPサーバとしてportsからmail/postfix_saslを入れて使う(成功)

- 仕方がないのでpkg install postfix-saslして頑張る。
  まずはsendmail廃止とpostfixインストール。

- sendmailを止める。
  ```
  # cd /etc/mail
  # make stop
  ```
   再起動時にsendmailが立ち上がらないように/etc/rc.conf(.local)に
   以下を書く
   ```
   sendmail_enable="NONE"
   ```
- pkgでmail/postfix-saslをインストールする。
   ```
   # pkg install postfix-sasl
   ```
- システムとしてsendmailの代わりにpostfixを使うためにmailer.confを
  入れる。
  ```
  # mkdir -p /usr/local/etc/mail
  # install -m 0644 /usr/local/share/postfix/mailer.conf.postfix /usr/local/etc/mail/mailer.conf
  ```
- /etc/rc.conf(.local)の手当て
  ```
  postfix_enable="YES"
  ```
- /etc/periodic.conf(.local)の手当て
  ```
  daily_clean_hoststat_enable="NO"
  daily_status_mail_rejects_enable="NO"
  daily_status_include_submit_mailq="NO"
  daily_submit_queuerun="NO"
  ```
- postfixの設定は
  [Amazon SESとPostfixの統合](https://docs.aws.amazon.com/ja_jp/ses/latest/DeveloperGuide/postfix.html)
  に従って行う。
- /usr/local/etc/postfix/main.cfの設定変更
   ```
   # postconf -e \
   "relayhost = [email-smtp.cc-direction-1.amazonaws.com]:587" \
   "smtp_sasl_auth_enable = yes" \
   "smtp_sasl_security_options = noanonymous" \
   "smtp_sasl_password_maps = hash:/usr/local/etc/postfix/sasl_passwd" \
   "smtp_use_tls = yes" \
   "smtp_tls_security_level = encrypt" \
   "smtp_tls_note_starttls_offer = yes"
   ```
   これでmain.cfにこの行が追加される。
- /usr/local/etc/postfix/master.cfにsmtp\_fallback_relayが存在しない
   ことを確認。
   ```
   # grep smtp_fallback_relay /usr/local/etc/postfix/master.cf
   ```
- /usr/local/etc/postfix/sasl\_passwdを新設して以下を書き込む。
   ```
   [email-smtp.cc-direction-1.amazonaws.com]:587 SMTPUSERNAME:SMTPPASSWORD
   ```
- ハッシュファイルを作る。
  ```
  # cd /usr/local/etc/postfix
  # postmap hash:sasl_passwd
  ```
- オーナとパーミッションを変更してパスワードを守る。
  ```
  # cd /usr/local/etc/postfix
  # chown root:wheel sasl_passwd sasl_passwd.db 
  # chmod 600 sasl_passwd sasl_passwd.db 
  # ls -l sasl_passwd sasl_passwd.db
  -rw-------  1 root  wheel     112 Oct 21 02:55 sasl_passwd
  -rw-------  1 root  wheel  131072 Oct 21 02:57 sasl_passwd.db
  ```
- CA証明書の位置をpostfixに教える。
  FreeBSDではpkgでca_root_nssをインストールすることでCA証明書を入手で
  き、実体ファイルは/usr/local/share/certs/ca-root-nss.crtにある。
  /etc/ssl/cert.pemがシンボリックリンクになっているのでこちらを使う。
  ```
  # postconf -e 'smtp_tls_CAfile =/etc/ssl/cert.pem'
  ```
- postfixを起動。
   ```
   # service postfix start
   ```
   statusとかstopとかrestartとかもある。
- /etc/aliases.dbが読めないと/var/log/maillogに出るので、
  `newaliases`コマンドを実行して再作成する。
  ```
  # newaliases
  ```
- これで以下の条件内のメール送信ができるようになるはず。
  - 送信側メールアドレスが登録済みの送信側ドメイン名の傘下のもの。
    (サブドメインも可であるようだ)
	(/etc/rc.conf.localでhostnameを登録済みドメイン名傘下のものに
	しておかないと自動補完されるドメイン名が違うものになって失敗する)
  - 受信側メールアドレスが登録済みのもの。
  - まだsandbox内なので、毎秒1通までとか一日200通(?)までとかの制限あり。
    毎秒1通制限にはpostfixの設定で対応する。
	```
	# postconf -e 'smtp_destination_concurrency_limit = 1' \
	'smtp_destination_rate_delay = 1s' \
    'smtp_extra_recipient_limit = 10'
	```
- daily checkのメール程度しかメールを出さない予定なので、sandbox脱出の
  申請は行わなかった。
