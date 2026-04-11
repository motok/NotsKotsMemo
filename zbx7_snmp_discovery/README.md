# Zabbix7でSNMPディスカバリ

## あらすじ

ひょんなことから、Zabbix7 を建てて SNMP によるデータ収集をすることになった。
それなりにハマったので、覚書を残しておきたい。

## 環境

- [倍控社の迷你工控机](https://bkhdpc.com/jisuanji/)の古いやつで、
  G30B-N5105だと思われる筐体。
  - ここに Ubuntu を入れて Zabbix サーバにする。
  - いわゆるミニPCで、ファンレス。
  - Celeron N5105 / 16GB メモリ / 128GB SSD / 2.5Gbps LAN * 4
  - 2.5Gbps のルータにしようと思ったら Intel I226-V で、通信ブツ切れ
    でどうにもならないやつだった。Ubuntuだとちょっとマシみたい。
  - [Ubuntu 24.04 LTS Server](https://jp.ubuntu.com/download)
    - 24.04.4 LTS (Noble Numbat)
    - apt upgrade済み
  - [PostgreSQL 16.13](https://www.postgresql.org/about/news/postgresql-183-179-1613-1517-and-1422-released-3246/)
    - apt でパッケージをインストール
  - [TimescaleDB 2.25.2](https://www.tigerdata.com/docs/self-hosted/latest/install/installation-linux#install-timescale_db-on-linux)
    - TimescaleDBのリポジトリを追加して、そこからパッケージをインストール。
  - [Zabbix 7.0 LTS](https://www.zabbix.com/download?zabbix=7.0&os_distribution=ubuntu&os_version=24.04&components=server_frontend_agent_2&db=pgsql&ws=nginx)
    - 7.0 LTS / Ubuntu / 24.04 (Noble) / Server, Frontend, Agent2 / PostgreSQL / Nginx
    - パッケージをダウンロードして dpkg -i でインストール。
- [NVR510](https://network.yamaha.com/products/routers/nvr510/index)
  - これを監視したい、Zabbixから、SNMPで。
  - [NVR510 SNMP MIBリファレンス](https://www.rtpro.yamaha.co.jp/RT/docs/snmp/snmp_mib_nvr510.html)
- [RTX1300](https://network.yamaha.com/products/routers/rtx1300/index)
  - これも監視したい、Zabbixから、SNMPで。
  - [RTX1300 SNMP MIBリファレンス](https://www.rtpro.yamaha.co.jp/RT/docs/snmp/snmp_mib_rtx1300.html)
- [NetSNMP](https://www.net-snmp.org)と各種MIB定義ファイル
  - snmp-mibs-downloaderパッケージも併せてaptでインストール。
  - YAMAHAのMIB定義ファイルももらってきて、これは手動でインストール。
    - [YAMAHA private MIB](https://www.rtpro.yamaha.co.jp/RT/docs/mib/)
      の
      [Archive file of all private MIB files.](https://www.rtpro.yamaha.co.jp/RT/docs/mib/yamaha-private-mib.tar.gz)
      を入れたので、YAMAHAのネットワーク機器なら大体大丈夫のはず。
- snmptranslateやsnmpwalkなどを用いてNVR510/RTX1300と通信できるように
  両側で設定しておく。
  - NVR510/RTX1300側は、SNMPv2でReadOnlyのコミュニティを設定。
  - Zabbixサーバ側は
    - プライベートMIBを/usr/share/snmp/の下に置いて
      ``` shell
      $ ls /usr/share/snmp
      mib2c-data/                    mib2c.iterate.conf
      mib2c.access_functions.conf    mib2c.mfd.conf
      mib2c.array-user.conf          mib2c.notify.conf
      mib2c.check_values_local.conf  mib2c.old-api.conf
      mib2c.check_values.conf        mib2c.perl.conf
      mib2c.column_defines.conf      mib2c.raw-table.conf
      mib2c.column_enums.conf        mib2c.scalar.conf
      mib2c.column_storage.conf      mib2c.table_data.conf
      mib2c.conf                     mibs/
      mib2c.container.conf           SensorDat.xml
      mib2c.create-dataset.conf      snmp_perl_trapd.pl
      mib2c.genhtml.conf             snmpconf-data/
      mib2c.int_watch.conf           yamaha-private-mib/
      mib2c.iterate_access.conf
      $ ls /usr/share/snmp/yamaha-private-mib/
      yamaha-product.mib.txt            yamaha-sw-firmware.mib.txt
      yamaha-rt-firmware.mib.txt        yamaha-sw-hardware.mib.txt
      yamaha-rt-hardware.mib.txt        yamaha-sw-l2ms.mib.txt
      yamaha-rt-interfaces.mib.txt      yamaha-sw-loop-detect.mib.txt
      yamaha-rt-ip.mib.txt              yamaha-sw-power-ethernet.mib.txt
      yamaha-rt-switch.mib.txt          yamaha-sw-ptp.mib.txt
      yamaha-rt.mib.txt                 yamaha-sw-rmon.mib.txt
      yamaha-smi.mib.txt                yamaha-sw-termmon.mib.txt
      yamaha-sw-bridge.mib.txt          yamaha-sw-vrrp.mib.txt
      yamaha-sw-errdisable.mib.txt      yamaha-sw.mib.txt
      ```
    - /etc/snmp/snmp.confで設定。
      ``` shell
      $ cat /etc/snmp/snmp.conf
      MIBDIRS /usr/share/snmp:/usr/share/snmp/mib2c-data:/usr/share/snmp/mibs:/usr/share/snmp/snmpconf-data:/usr/share/snmp/yamaha-private-mib
      MIBS all
      ```
    - ~/.snmp/snmp.conf にSNMPv2でこのコミュニティだよと設定。
      ``` shell
      $ cat ~/.snmp/snmp.conf 
      defVersion 2c
      defCommunity superdupersecret
      ```
- 後述のホストディスカバリやアイテムディスカバリは、僕が勝手に呼んでいる名称。
  ややこしいので別の用語で呼んだという以上の意味はない。

## SNMPによるデータ収集のあらすじ

SNMPによるデータ収集は、次のような順で行われる。

- ホストディスカバリ(Zabbixでいう無印のディスカバリ)
  - せっかくなので SNMP で機種のデータを取りに行って、
  - NVR510/RTX1300だという条件にあえばホストを登録する。
  - その時に、収集するべきデータを記述したテンプレートを割り当てる。
- テンプレートには、データ収集するべきアイテムを登録してある。
  - 例えば標準MIBの RFC1213-MIB::sysName のように
    そのノードに一つしかないであろうものは後述のアイテムディスカバリをするまでもなく
    テンプレートのアイテムのところに書いておけば足りる。
  - でも、CPUコア別の使用率とかネットワークインタフェース毎のトラフィック(bpsとかppsとか）
    のようなものだと、機種によってはカードで増設できたりするので次のアイテムディスカバリで
    検出する方が好ましいかもしれない。
- アイテムディスカバリ(Zabbixでいうローレベルディスカバリ = LLD)
  - テンプレートの(アイテム)ディスカバリルールに従ってアイテム候補を発見し、
  - 取捨選択してアイテムを登録する。
- これで、自動的にホストを発見して、そのホストにあるアイテムを列挙して
  データを収集することになる。
- テンプレートには、ダッシュボードやグラフの設定も書けるので、
  必要なら追加しておくと良いかもしれない。

## ホストディスカバリ

- Zabbix から SNMP で RFC1213-MIB::sysDescr.0 を取ってきて、それが
  NVR510/RTX1300 のものだったら監視対象に追加する、という論理。
  - ICMP echoに応答があれば追加とかもできるけど、それだと他のノードも
    追加してしまうので、一応機種まで見ることにした。
  - 今回は SNMPv2 でコミュニティ(RO)を設定してあるので、例え NVR510/RTX1300 で
    あっても別のコミュニティのノードは検出しない。

- コマンドラインではこんな感じで応答が返ってくる。
  ``` shell
  $ snmptranslate -Of .1.3.6.1.2.1.1.1.0
  .iso.org.dod.internet.mgmt.mib-2.system.sysDescr.0
  
  $ snmptranslate .1.3.6.1.2.1.1.1.0
  RFC1213-MIB::sysDescr.0
  
  $ snmpwalk 10.227.0.254 .1.3.6.1.2.1.1.1.0
  RFC1213-MIB::sysDescr.0 = STRING: "NVR510 Rev.15.01.26 (Fri Aug 23 10:36:30 2024)"
  ```

### SNMP でホストディスカバリをさせる

まず、Zabbix から SNMP でスキャンしてホストを探すように設定する。

そのためには、「Zabbix/データ収集/ディスカバリ」でディスカバリルールを追加する。
これによって、指定したIPアドレス群に対して指定した方法でホストディスカバリのためのスキャンを行う。

  <img src="./01_host_discovery_rule.png" width=65%>ディスカバリルール<img/>

| 項目 | 設定内容 |
| ---- | -------|
| 名前 | 適宜、名前を付ける。|
| ディスカバリの実行 | 今回はプロクシZabbixノードを使っていないので、「サーバ」を選択。 |
| IPアドレスの範囲 | 指定されたIPアドレス(の範囲)について、ホストディスカバリを行う。今回はNVR510のアドレス１個だけに限定。 |
|                | 192.168.0.100 等と書けば /32 指定であるらしい。 |
|                | 192.168.0.0/24 などとも書ける。 |
|                | 192.168.0.1-3 と書けば、192.168.0.1 から 192.168.0.3 までの 3 IP。 |
|                | 192.168.5-6.254 と書けば、192.168.5.254 と 192.168.6.254 らしい。 |
|                | 複数を並べる時はカンマ区切り 192.168.0.100,10.0.0.0/24 |
| 監視間隔 | 運用時はデフォルトの 1h でいいと思うけど、検証中は 5m くらいでよいのではないか。 |
| タイプごとの探索の最大並列実行数 | デフォルトでは無制限だが、カスタムで絞っておく方が良いのではないか。ディスカバリ間隔との兼ね合いで決める。 |
| 探索方法 | 「追加」をクリックすると「ディスカバリチェック」の画面がポップアップするので、適切な探索方法を構成する。(後述) |
| デバイスの固有性を特定する基準 | IPアドレスを指定。上で指定した SNMP OID だと機種が返されるので、固有性を特定できない。 |
| ホスト名 | デフォルトのDNS名でもよさそう。 |
| 表示名 | デフォルトのホスト名で良さそう。 |
| 有効 | 有効にしておけばホストディスカバリを開始する。 |

探索方法の設定は次の通り。SNMPで機種の情報を取得できたら発見したという扱いになる。
機種がNVR510/RTX1300であるかどうかのチェックは次のディスカバリアクションに設定する。

  <img src="./02_snmpv2_config.png" width=40%>ディスカバリチェック<img/>

| 項目 | 設定内容 |
| ---- | -------|
| 探索方法のタイプ | SNMPv2 エージェント |
| ポート | デフォルトの 161 |
| SNMPコミュニティ | NVR510 と通信できるもの(上記のコマンドラインを参照) |
| SNMP OID | 上記の RFC1213-MIB::sysDescr.0 の OID を指定。機種がわかる。|

### スキャンへの応答を調べて、条件に合えば登録作業を行う

次に、スキャンへの応答を調べて、条件に合うかどうかを調べ、合えば監視
対象としてホストを登録する。
その際に、テンプレートを割り当ててアイテムディスカバリを可能にする。

そのためには、「Zabbix/通知/アクション/ディスカバリアクション」でアクションを作成する。
アクションは、「アクション」と「実行内容」の２個のタブに分かれている (ややこしい)。

#### 「アクション」タブ

  <img src="./03_action-action.png" width=65%>アクション/アクションタブ<img/>

| 項目 | 設定内容 |
| ---- | -------|
| 名前 | 適宜、名前を付ける。 |
| 計算のタイプ | この後の「実行条件」をANDで結ぶのか、ORで結ぶのか、同一条件部分だけORで結んで異なる条件同士はANDで結ぶのか。 |
| 実行条件 A | 先ほど作成した「(ホスト)ディスカバリルール」を指定する。そのルールでスキャンに応答してきたものをこれ以降の条件に合うかどうか調べよということ。 |
| 実行条件 B | 「受信した値」が "NVR510" を含むという条件。|
| 実行条件 C | 「アップタイム/ダウンタイム」が 600 秒以上であるという条件。ある程度の時間に渡って安定して存在/不在のときに登録/解除をやるということ。 |
| 有効 | 有効にしておくとこのアクションが作動する。 |

これで、`A and B and C` という論理式で真になれば、そのノードに対して後述の「実行内容」タブの内容を実行することになる。

ちょっと脱線して、機種がNVR510かRTX1300かのいずれかなら真になるようにするには、
次の図のようにすれば良い。
「実行条件C」に「機種がRTX1300」という条件が増えていて、「計算のタイプ」が「And/Or」になっている点に注意。
これで、同じ項目(ここでは「受信した値」)に対して複数の条件を定義すると、そこだけ OR になって、他の項目との間では AND で結ばれる。

  <img src="./03-2_action-action.png" width=65%>アクション/アクションタブ<img/>


#### 「実行内容」タブ

「(ホスト)ディスカバリ」のルールで見つけてきたホストの候補に対して、
「アクション」タブの条件で絞り込みを行った。
絞り込みの条件に合致したホスト候補について、この「実行内容」タブの内容を実行する。

  <img src="./04_action-execution.png" width=60%>アクション/実行内容タブ<img/>


| 項目 | 設定内容 |
| ---- | -------|
| ホストを追加 | 監視対象としてホストを登録する。 |
| ホストグループに追加 | 「NVR510ホストグループ」(←あらかじめ作成済み)に追加する。 |
| テンプレートをリンク | 「YAMAHA NVR510 by SNMP」テンプレート(←後述)にリンクする。とりあえずリンクするなら「Network Generic Device by SNMP」でも良い。 |

- これでホストディスカバリは完了し、条件にあったノードをZabbix監視対象の登録・ホストグループへの追加・テンプレート適用などの作業を実施したことになる。


## テンプレート作成

前節ホストディスカバリで、条件に合うノードを監視対象として登録し、テンプレートを適用するところまではできた。
本節では、そのテンプレートを作成する。

テンプレートは、「Zabbix/データ収集/テンプレート」で「テンプレートの作成」をクリックして作成する。
とりあえず、「YAMAHA NVR510 by SNMP」というテンプレートを作成したのが次の図である。

  <img src="./10_create-template.png" width=60%>YAMAHA NVR510 by SNMP テンプレート作成<img/>

| 項目 | 設定内容 |
| ---- | -------|
| テンプレート名 | 適宜、名前を付ける。 |
| 表示名 | 日本語の名前を付けるとかならここへ書く。ここでは空欄にしたのでテンプレート名に同じ。 |
| テンプレート | ここでは空欄にした。既存のテンプレート名を書くと、そのテンプレートから項目などを継承するみたい。 |
| テンプレートグループ | このテンプレートが属するテンプレートグループを指定。すべてのテンプレートがTemplatesグループに所属する慣習のようなのでそれを書いておくのと、ネットワークデバイス用のテンプレートだよなということで Templates/Network devices を書いておく。 |
| 説明 | 良い子は説明をしっかり書きましょう。 |












