# Zabbix 7 LTS on FreeBSD

Ubuntu をはじめとする Linux 上に Zabbix をインストールするなら
[Download and install Zabbix](https://www.zabbix.com/jp/download?zabbix=7.0&os_distribution=ubuntu&os_version=24.04&components=server_frontend_agent&db=pgsql&ws=nginx)
のページの指示通りにやれば簡単にインストールできる。
僕の場合はたいてい Ubuntu にインストールしていて、
そういえば FreeBSD にインストールしたことがないかもしれない。
ということで Zabbix 7 LTS を FreeBSD にインストールする手順をメモしておく。
(2026-07-23)

## 使用したバージョン

- FreeBSD 15.1-RELEASE-p1
- Zabbix 7.0 LTS (7.0.28)
- PostgreSQL 18.4

## パッケージからのインストール

- Zabbix は DBMS (MySQL/PostgreSQL) や Web サーバ (apache/nginx) を必要とするので、
  併せてパッケージ (Ports) からインストールしておく。
  ```
  # pkg update
  # pkg install zabbix7-server
  # pkg install postgresql18-server
  # pkg install nginx
  ```

## PostgreSQL の初期設定

- [FreeBSD wiki: PostgreSQL](https://wiki.freebsd.org/PostgreSQL/Setup)
  を参考にして、まず PostgreSQL の初期設定を行う。

- `sysrc postgresql_enable="YES"`
  - 僕の場合は `vi /etc/rc.conf.local` から手で書いちゃうけれど、いずれにしても
    postgresql デーモンを動かす設定。

- `service postgresql initdb`
  - PostgreSQL としては `initdb` という単独のコマンドでデータベース領域
    (/var/db/postgres/) を初期化する。
  - service コマンドを使って上記のようにしても同じことができる。
    (/usr/local/etc/rc.d/postgresql を参照)
  - これで、/var/db/postgres/data18/ ディレクトリが作成されて、
    各種設定ファイルなどがここに置かれる。
  - 蛇足ながら、この initdb は、インストール時に一度だけ実行するものである。

- `service postgresql start`
  - とりあえず、postgresql デーモンを立ち上げて、動作確認 `service postgresql status`
  - `sockstat -46 -p 5432` で待受ポートの IP アドレスとポート番号を確認。
    - 127.0.0.1 と ::1 の 5432/tcp で待ち受けているはず。
    - UNIX ドメインソケットは /tmp/.s.PGSQL.5432

- OS ユーザの postgres にパスワードを付与。
  - `sudo passwd postgres`

- DB ユーザの postgres にもパスワードを付与。
  - ```
    $ sudo su - psql
    $ psql
    > ALTER ROLE posgres WITH ENCRYPTED PASSWORD 'superdupersecret';
    ```

- PostgreSQL へのログイン時の認証設定を変更
  - デフォルトでは、localhost からの接続は trust されていて認証無しで DB ログイン可能。
  - どこからアクセスしても、パスワード認証するように変更する。
  - `vi /var/db/postgres/data18/pg_hba.conf`
    ```
    # diff -u pg_hba.conf.orig pg_hba.conf
    --- pg_hba.conf.orig	2026-07-23 16:15:09.734234000 +0900
    +++ pg_hba.conf	2026-07-22 16:53:39.538404000 +0900
    @@ -114,13 +114,13 @@
     # TYPE  DATABASE        USER            ADDRESS                 METHOD

     # "local" is for Unix domain socket connections only
    -local   all             all                                     trust
    +local   all             all                                     scram-sha-256
     # IPv4 local connections:
    -host    all             all             127.0.0.1/32            trust
    +host    all             all             127.0.0.1/32            scram-sha-256
     # IPv6 local connections:
    -host    all             all             ::1/128                 trust
    +host    all             all             ::1/128                 scram-sha-256
     # Allow replication connections from localhost, by a user with the
     # replication privilege.
    -local   replication     all                                     trust
    -host    replication     all             127.0.0.1/32            trust
    -host    replication     all             ::1/128                 trust
    +local   replication     all                                     scram-sha-256
    +host    replication     all             127.0.0.1/32            scram-sha-256
    +host    replication     all             ::1/128                 scram-sha-256
    ```
  - `service postgresql restart` で設定変更を適用。

- .pgpass ファイルの設定
  - PostgreSQL では、OS ユーザの ~/.pgpass を設定しておくことで、psql でのパスワード入力を自動化できる。
    ```
    # ~/.pgpass
    # hostname:port:database:username:password
    *:*:*:postgres:superdupersecret
    ```
  - psql に与える DB ユーザ名は、
    - デフォルトでは OS ユーザ名を使う
    - 環境変数 PGUSER に設定しておけばその DB ユーザ名を使ってくれる。
    - `psql -U postgres` のようにコマンドラインオプションで指定することもできる。

## Zabbix のために PostgreSQL を設定する

- PostgreSQLにzabbixユーザとzabbixデータベースを作成する
  - [(Zabbixの)データベースの作成](https://www.zabbix.com/documentation/7.0/jp/manual/appendix/install/db_scripts)
  - 既存データベースの一覧表示: `\l`
  - 既存ユーザ(ロール)の一覧表示: `SELECT * FROM pg_user;`
  - CREATE USER zabbix WITH ENCRYPTED PASSWORD 'superdupersecret';
  - CREATE DATABASE zabbix OWNER zabbix;










