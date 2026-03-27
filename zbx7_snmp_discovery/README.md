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
  - これをZabbixからSNMPで監視したい。
  - [NVR510 SNMP MIBリファレンス](https://www.rtpro.yamaha.co.jp/RT/docs/snmp/snmp_mib_nvr510.html)
- [NetSNMP](https://www.net-snmp.org)と各種MIB定義ファイル
  - snmp-mibs-downloaderパッケージも併せてaptでインストール。
  - NVR510用のMIB定義ファイルももらってきて、これは手動でインストール。
    - [YAMAHA private MIB](https://www.rtpro.yamaha.co.jp/RT/docs/mib/)
      の
      [Archive file of all private MIB files.](https://www.rtpro.yamaha.co.jp/RT/docs/mib/yamaha-private-mib.tar.gz)
      を入れたので、YAMAHAのネットワーク機器なら大体大丈夫のはず。
- snmptranslateやsnmpwalkなどを用いてNVR510と通信できるように
  両側で設定しておく。

## ホストディスカバリ

- Zabbix から SNMP で RFC1213-MIB::sysDescr.0 を取ってきて、それが
  NVR510 のものだったら監視対象に追加する、という論理。
  - ICMP echoに応答があれば追加とかもできるけど、それだと他のノードも
    追加してしまうので、一応機種まで見ることにした。
  - 今回は SNMPv2 でコミュニティ(RO)を設定してあるので、例え NVR510 で
    あっても別のコミュニティのノードは検出しない。

- コマンドラインからはこんな感じで応答が返ってくる。
  ``` shell
  $ cat ~/.snmp/snmp.conf
  defVersion 2c
  defCommunity superDuperSecret
  $ snmpget 10.227.0.254 .1.3.6.1.2.1.1.1.0
  RFC1213-MIB::sysDescr.0 = STRING: "NVR510 Rev.15.01.26 (Fri Aug 23 10:36:30 2024)"
  ```

- まず、Zabbix から SNMP でスキャンしてホストを探すために、
  「Zabbix/データ収集/ディスカバリ」でディスカバリルールを追加する。
  - 名前: 適宜、名前を付ける。
  - ディスカバリの実行: 今回はプロクシZabbixノードを使っていないので、
    「サーバ」を選択。
  - IPアドレスの範囲: 図中では 192.168/24 に限定している。適切な範囲に
    書き換える。
    - 複数の範囲があるときはカンマで区切って並べる。
    - 192.168.0.100 等と書けば /32 指定であるらしい。
    - 192.168.0.0/24 などとも書ける。
    - 192.168.0.1-3 と書けば、192.168.0.1 から 192.168.0.3 までの 3 IP。
    - 192.168.5-6.254 と書けば、192.168.5.254 と 192.168.6.254 らしい。
      (本当？
  - 監視間隔: 運用時はデフォルトの 1h でいいと思うけど、検証中は 5m く
    らいでよいのではないか。
  - タイプごとの探索の最大並列実行数: デフォルトでは無制限だが、カスタ
    ムで 16 くらいが良いのではないか。監視間隔との兼ね合いもある。
  - 探索方法: 「追加」をクリックすると「ディスカバリチェック」の画面が
    ポップアップするので、適切な探索方法を構成する。
    - 今回は、「SNMPv2 エージェント」で
    - ポートはデフォルトの 161 、
    - SNMPコミュニティは NVR510 と通信できるもの(上記のコマンドライン
      を参照)、
    - SNMP OID は上記の sysDescr.0 の OID を指定。
  - デバイスの固有性を特定する基準: IPアドレスを指定。
    - 上で指定した SNMP OID だと機種が返されるので、固有性を特定できな
      い。
  - ホスト名: デフォルトのDNS名でよさそう。
  - 表示名: デフォルトのホスト名で良さそう。
  - 有効: 有効にしておけばホストディスカバリを開始する。デフォルトでは
    無効の状態だが、検証環境なら有効にしておけば良いのではないか。

  <img src="./01_host_discovery_rule.png" width=65%>新規ディスカバリルールの図<img/>
  <img src="./02_snmpv2_config.png" width=30%>ディスカバリチェックの図<img/>





















