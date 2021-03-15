# PostgreSQLインストールと初期設定の覚え書き

[[_TOC_]]

## これは何

- PostgreSQLのインストール時の初期設定を毎回忘れるので自分のための覚え書き。

## 編集履歴

- 2021/Mar/15頃作成 FreeBSD-12.2-RELEASEとdatabases/postgresql13-server (-clientも)

## databases/postgresql13-serverをインストールする

- FreeBSD12.2でportsからpostgresql13をインストールする。

  ```shell
  # pkg install postgresql13-server
  Updating FreeBSD repository catalogue...
  Fetching packagesite.txz: 100%    6 MiB   6.4MB/s    00:01    
  Processing entries: 100%
  FreeBSD repository update completed. 30177 packages processed.
  All repositories are up to date.
  Checking integrity... done (0 conflicting)
  The following 2 package(s) will be affected (of 0 checked):
  
  New packages to be INSTALLED:
  	postgresql13-client: 13.1
  	postgresql13-server: 13.1_1
  
  Number of packages to be installed: 2
  
  The process will require 53 MiB more space.
  
  Proceed with this action? [y/N]: y
  [1/2] Installing postgresql13-client-13.1...
  [1/2] Extracting postgresql13-client-13.1: 100%
  [2/2] Installing postgresql13-server-13.1_1...
  ===> Creating groups.
  Using existing group 'postgres'.
  ===> Creating users
  Using existing user 'postgres'.
  ===> Creating homedir(s)
  
    =========== BACKUP YOUR DATA! =============
    As always, backup your data before
    upgrading. If the upgrade leads to a higher
    major revision (e.g. 9.6 -> 10), a dump
    and restore of all databases is
    required. This is *NOT* done by the port!
    See https://www.postgresql.org/docs/current/upgrading.html
    ===========================================
  [2/2] Extracting postgresql13-server-13.1_1: 100%
  =====
  Message from postgresql13-client-13.1:
  
  --
  The PostgreSQL port has a collection of "side orders":
  
  postgresql-docs
    For all of the html documentation
  
  p5-Pg
    A perl5 API for client access to PostgreSQL databases.
  
  postgresql-tcltk 
    If you want tcl/tk client support.
  
  postgresql-jdbc
    For Java JDBC support.
  
  postgresql-odbc
    For client access from unix applications using ODBC as access
    method. Not needed to access unix PostgreSQL servers from Win32
    using ODBC. See below.
  
  ruby-postgres, py-psycopg2
    For client access to PostgreSQL databases using the ruby & python
    languages.
  
  postgresql-plperl, postgresql-pltcl & postgresql-plruby
    For using perl5, tcl & ruby as procedural languages.
  
  postgresql-contrib
    Lots of contributed utilities, postgresql functions and
    datatypes. There you find pg_standby, pgcrypto and many other cool
    things.
  
  etc...
  =====
  Message from postgresql13-server-13.1_1:
  
  --
  For procedural languages and postgresql functions, please note that
  you might have to update them when updating the server.
  
  If you have many tables and many clients running, consider raising
  kern.maxfiles using sysctl(8), or reconfigure your kernel
  appropriately.
  
  The port is set up to use autovacuum for new databases, but you might
  also want to vacuum and perhaps backup your database regularly. There
  is a periodic script, /usr/local/etc/periodic/daily/502.pgsql, that
  you may find useful. You can use it to backup and perform vacuum on all
  databases nightly. Per default, it performs `vacuum analyze'. See the
  script for instructions. For autovacuum settings, please review
  ~pgsql/data/postgresql.conf.
  
  If you plan to access your PostgreSQL server using ODBC, please
  consider running the SQL script /usr/local/share/postgresql/odbc.sql
  to get the functions required for ODBC compliance.
  
  Please note that if you use the rc script,
  /usr/local/etc/rc.d/postgresql, to initialize the database, unicode
  (UTF-8) will be used to store character data by default.  Set
  postgresql_initdb_flags or use login.conf settings described below to
  alter this behaviour. See the start rc script for more info.
  
  To set limits, environment stuff like locale and collation and other
  things, you can set up a class in /etc/login.conf before initializing
  the database. Add something similar to this to /etc/login.conf:
  ---
  postgres:\
  	:lang=en_US.UTF-8:\
  	:setenv=LC_COLLATE=C:\
  	:tc=default:
  ---
  and run `cap_mkdb /etc/login.conf'.
  Then add 'postgresql_class="postgres"' to /etc/rc.conf.
  
  ======================================================================
  
  To initialize the database, run
  
    /usr/local/etc/rc.d/postgresql initdb
  
  You can then start PostgreSQL by running:
  
    /usr/local/etc/rc.d/postgresql start
  
  For postmaster settings, see ~pgsql/data/postgresql.conf
  
  NB. FreeBSD's PostgreSQL port logs to syslog by default
      See ~pgsql/data/postgresql.conf for more info
  
  NB. If you're not using a checksumming filesystem like ZFS, you might
      wish to enable data checksumming. It can only be enabled during
      the initdb phase, by adding the "--data-checksums" flag to
      the postgres_initdb_flags rcvar.  Check the initdb(1) manpage
      for more info and make sure you understand the performance
      implications.
  
  ======================================================================
  
  To run PostgreSQL at startup, add
  'postgresql_enable="YES"' to /etc/rc.conf
  ```

- `/etc/rc.conf`に追記

  ```shell
  postgresql_enable="YES"
  ```

- 一回だけデータベースの初期化を行う。これによって`/var/db/postgres/data13`以下に設定ファイルやデータベースファイルなどが生成される。

  ```shell 
  # service postgresql initdb
  The files belonging to this database system will be owned by user "postgres".
  This user must also own the server process.
  
  The database cluster will be initialized with locale "C".
  The default text search configuration will be set to "english".
  
  Data page checksums are disabled.
  
  creating directory /var/db/postgres/data13 ... ok
  creating subdirectories ... ok
  selecting dynamic shared memory implementation ... posix
  selecting default max_connections ... 100
  selecting default shared_buffers ... 128MB
  selecting default time zone ... Asia/Tokyo
  creating configuration files ... ok
  running bootstrap script ... ok
  performing post-bootstrap initialization ... ok
  syncing data to disk ... ok
  
  initdb: warning: enabling "trust" authentication for local connections
  You can change this by editing pg_hba.conf or using the option -A, or
  --auth-local and --auth-host, the next time you run initdb.
  
  Success. You can now start the database server using:
  
      /usr/local/bin/pg_ctl -D /var/db/postgres/data13 -l logfile start
  ```

- これでデータベースのプロセスを起動することができる。

  ```shell
  # service postgresql start
  2021-03-15 15:55:39.862 JST [51410] LOG:  ending log output to stderr
  2021-03-15 15:55:39.862 JST [51410] HINT:  Future log output will go to log destination "syslog".
  
  # service postgresql status
  pg_ctl: server is running (PID: 51410)
  /usr/local/bin/postgres "-D" "/var/db/postgres/data13"
  ```

- この時、待受ポートは`localhost:5432`と`/tmp`下の`UNIX socket`。

  ```shell
  # netstat -na | grep 5432
    tcp4    0   0 127.0.0.1.5432     *.*          LISTEN   
    tcp6    0   0 ::1.5432           *.*          LISTEN   
    fffff8000392b800 stream 0 0 fffff800297d15a0 0 0 0 /tmp/.s.PGSQL.5432
  # ls -l /tmp/.s.PGSQL.5432*
    srwxrwxrwx 1 postgres wheel  0 Mar 15 15:55 /tmp/.s.PGSQL.5432=
    -rw------- 1 postgres wheel 51 Mar 15 15:55 /tmp/.s.PGSQL.5432.lock
  ```

  

- 特権ユーザに当たる`postgres`ロールを指定する必要があるが、パスワードを聞かれることもなく`psql`コマンドで接続して使えるはず。

  ```shell
  # psql
  psql: error: FATAL:  role "root" does not exist
  
  # psql -U postgres
  psql (13.1)
  Type "help" for help.
  
  postgres=# SELECT rolname, rolsuper, rolcanlogin FROM pg_roles;
            rolname          | rolsuper | rolcanlogin 
  ---------------------------+----------+-------------
   postgres                  | t        | t
   pg_monitor                | f        | f
   pg_read_all_settings      | f        | f
   pg_read_all_stats         | f        | f
   pg_stat_scan_tables       | f        | f
   pg_read_server_files      | f        | f
   pg_write_server_files     | f        | f
   pg_execute_server_program | f        | f
   pg_signal_backend         | f        | f
  (9 rows)
  ```
  
- すかさず<u>`postgres`ロールにパスワードを付与</u>する。

  ```shell
  # psql -U postgres
  psql (13.1)
  Type "help" for help.
  
  postgres=# ALTER ROLE postgres WITH PASSWORD 'secret';
  ALTER ROLE
  ```

- パスワードを付与したにもかかわらず、パスワードを入力することなくログインできる。これは、`postgresql`デーモンの設定でパスワードを要求することなくログインさせる設定になっているからである。

  ```shell
  # psql -U postgres
  psql (13.1)
  Type "help" for help.
  
  postgres=# 
  ```

## 接続時にパスワードを要求する設定

- 設定ファイルは前述の通り`/var/db/postgres/data13`以下にある。

- `postgresql.conf`でパスワード認証にデフォルトのmd5ではなくより強い(はずの)scram-sha-256を使うように指定する。

  ```shell
  # diff -u postgresql.conf.orig postgresql.conf
  --- postgresql.conf.orig	2021-03-15 12:25:36.268064000 +0900
  +++ postgresql.conf	2021-03-15 12:25:56.694505000 +0900
  @@ -89,6 +89,7 @@
  
   #authentication_timeout = 1min		# 1s-600s
   #password_encryption = md5		# md5 or scram-sha-256
  +password_encryption = scram-sha-256
   #db_user_namespace = off
   
   # GSSAPI using Kerberos
  ```

- `pg_hba.conf`で`UNIX domain`ソケット(`local`)以外の接続でscram-sha-256によるパスワード認証を要求するように指定する。この後の設定でログインできなくなった場合はここを戻して`reload`すれば良い。

  ```shell
  # diff -u pg_hba.conf.orig pg_hba.conf
  --- pg_hba.conf.orig	2021-03-15 12:16:25.137500000 +0900
  +++ pg_hba.conf	2021-03-15 12:27:00.062449000 +0900
  @@ -85,13 +85,13 @@
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

- `reload`して設定を有効にする。

  ```shell
  # service postgresql reload
  ```

- もう一度`psql`で接続してみると、パスワードを要求されて正しく入力するとログインできる。特に指定していないので、これは`UNIX domain`ソケットに対する接続である。

  ```shell
  # psql -U postgres
  Password for user postgres: ******
  psql (13.1)
  Type "help" for help.
  
  postgres=# 
  ```

- `127.0.0.1:5432`に接続に行くと、こちらもパスワードを与えてログインできる。

  ```shell
  # psql -U postgres -h 127.0.0.1
  Password for user postgres: ******
  psql (13.1)
  Type "help" for help.
  
  postgres=# 
  ```

## 個人環境の手入れ

- ロール名やパスワードを毎回指定しなくてすむように、個人環境の設定を行う。

- 環境変数と個人設定ファイルを用いてロール指定や接続先ホスト名を省略してログインすることができる。

- まず環境変数の設定。適宜、~/.bash_profile等で環境変数を設定しておくと良い。

  ```shell
  # PGHOST=/tmp;                export PGHOST
  # PGDATABASE=postgres;        export PGDATABASE
  # PGUSER=postgres;            export PGUSER
  # PGPASSFILE=${HOME}/.pgpass; export PGPASSFILE
  ```

- 続いて.pgpassファイルの設定。

  - 指定に合わせて${HOME}/.pgpassを使う。
  - 他のユーザから読まれることのないようにpermissionを変更しておく。
  - カラムは順に、接続先ホスト：ポート番号：データベース：ロール：パスワード
  - 接続先ホストを`UNIX domain`ソケットにするには、ソケットファイルのあるディレクトリ(ここでは`/tmp`)とすれば良い。この時ポート番号は書かない。
  - `::1`しか試していないが、IPv6アドレスは鉤括弧[]でくるまなくてもそのまま書けるようだ。

  ```shell
  # touch ${HOME}/.pgpass
  # chmod 600 ${HOME}/.pgpass
  # cat << EOF > ${HOME}/.pgpass
  /tmp::postgres:postgres:secret
  localhost:5432:postgres:postgres:secret
  127.0.0.1:5432:postgres:postgres:secret
  ::1:5432:postgres:postgres:secret
  EOF
  ```

- これでロール名やパスワード入力を省略してログインができる。

  ```shell
  # psql
  psql (13.1)
  Type "help" for help.
  
  postgres=# 
  ```

- `.pgpass`の設定があるにも関わらず、パスワード入力を強制させたい場合には

  ```shell
  # psql -W
  Password: ******
  psql (13.1)
  Type "help" for help.
  
  postgres=# 
  ```

## パフォーマンス調整等

-  勉強せねば。