# portsでデフォルトのconfigを変更したい

## これは何？
- FreeBSD (今使っているのは 12.2R) には
  [ports](https://docs.freebsd.org/en/books/handbook/ports/)
  と呼ばれる各種アプリケーションを追加する仕組みがある。
- [狭義のports](https://docs.freebsd.org/en/books/handbook/ports/#ports-using)
  では、通常 /usr/ports/ 以下にファイルを展開しておいて、使いたいアプ
  リケーションのディレクトリで make でコンパイル・インストールをするこ
  とになる。
- 最近はコンパイル済みのバイナリパッケージをダウンロードしてインストー
  ルする
  [pkg](https://docs.freebsd.org/en/books/handbook/ports/#pkgng-intro)
  の仕組みが主流になっている。
- バイナリパッケージで事が済めばそれで構わないが、時にはバイナリパッケー
  ジにおける config オプションでは不足で、どうしても `make
  config` してコンパイルしなければならない場合が出てくる。(出てこない？)
  特定のアプリケーションだけをコンパイルしてインストールするが、その他
  のほとんどのアプリケーションはバイナリパッケージをインストールする、
  という運用がなんの問題もなくできるのは、実は凄い事だと思う。(関係者
  に感謝を！)
- ところが、しばらくしてからバイナリパッケージで更新をかけると、ついつ
  い「これだけはコンパイルしなければいけなかったのに！」というアプリケー
  ションを忘れていて、期待の動作をしない事件が起きる。
  - 例：dns/nsd で dnstap を使いたいのでそのオプションを追加して
    コンパイルしたのに、数ヶ月後には忘れていてバイナリパッケージで上書
    きしちゃった。コンパイルしなければならないのは思い出したけど、どの
    オプションが必要だったか覚えてない！
- そういう時にはどうするのか、ということで、いくつかメモしておく。

## バイナリパッケージで上書き更新しないようにロックする

- 例として japanese/nkf をバイナリパッケージでインストールするならこん
  な感じ。
  ``` shell
  # pkg search nkf
  pkg search nkf
  ja-nkf-2.1.4,1                 Network Kanji code conversion Filter
  ja-p5-nkf-2.1.4,1              Perl extension module to use NKF
  junkfilter-20030115_1          Spam filtering software for procmail
  rubygem-nkf-0.1.1              Ruby extension for Network Kanji Filter

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
  [1/1] Fetching ja-nkf-2.1.4,1.pkg: 100%  150 KiB 153.8kB/s    00:01    
  Checking integrity... done (0 conflicting)
  [1/1] Installing ja-nkf-2.1.4,1...
  [1/1] Extracting ja-nkf-2.1.4,1: 100%
  ```
- このパッケージをバイナリパッケージで上書き更新しないように「ロック」
  する。
  ``` shell
  # pkg lock ja-nkf
  ja-nkf-2.1.4,1: lock this package? [y/N]: y
  Locking ja-nkf-2.1.4,1

  # pkg lock -l
  Currently locked packages:
  ja-nkf-2.1.4,1
  ```
- これで削除ができなくなる。
  ``` shell
  # pkg remove ja-nkf
  Checking integrity... done (0 conflicting)
  The following package(s) are locked and may not be removed:

  	ja-nkf

  1 packages requested for removal: 1 locked, 0 missing
  ```
- 実験できていないけれど、多分これで上書き更新 `pkg upgrade ja-nkf` 
  できないはず。

## /etc/make.conf に ports の config オプションを書く

- 例として dns/nsd で、デフォルトでは off の dnstap オプションを on に
  したい場合を考える
- /usr/ports/ 下に ports ツリーを展開するには
  ``` shell
  # portsnap auto
  ```
- dns/nsd へ行って以降の作業を行う。
  ``` shell
  # cd /usr/ports/dns/nsd
  ```
- ports のデフォルトで指定されている config オプションを調べる。
  ``` shell
  # make -VOPTIONS_DEFAULT
  BIND8_STATS LARGEFILE MINRESPSIZE NSEC3 RADIXTREE RRL ZONE_STATS
  ```
- 手動で変更するなら `make (re)config` でできるが、面倒かつ忘れるので
  困る。そこで、`/etc/make.conf` に書いておくようにしたい。
  蛇足ながら `make config` すると /var/db/ports/ 以下に設定が書き込ま
  れる。それを削除するには `make rmconfig`
- 指定できるオプションを列挙するには
  ``` shell
  # make -VCOMPLETE_OPTIONS_LIST
  BIND8_STATS CHECKING DNSTAP DOCS IPV6 LARGEFILE MINRESPSIZE MMAP MUNIN_PLUGIN NSEC3 PACKED RADIXTREE ROOT_SERVER RRL ZONE_STATS
  ```
- 今指定しているオプションを列挙するには
  ``` shell
  # make -VPORT_OPTIONS
  BIND8_STATS DNSTAP DOCS IPV6 LARGEFILE MINRESPSIZE NSEC3 RADIXTREE RRL ZONE_STATS
  ```
  (これより前に `make config` で DNSTAP を有効にしていたのでデフォルト
  設定と差異がある。)
- `/etc/make.conf` に書く時にこのパッケージを指定する識別子になる文字
  列を調べるには、
  ``` shell
  # make -VOPTIONS_NAME
  dns_nsd
  ```
- `/etc/make.conf` に設定を書いておくには、{パッケージ識別子}_SET なる
  変数 (dns_nsd_SET) に、on にしたいオプション名 (DNSTAP) を書けばよい。
  複数ある場合は空白で区切って列挙。
  ``` shell
  # echo "dns_nsd_SET= DNSTAP" >> /etc/make.conf
  ```

## ワークフロー
- 手動でやるなら初回はこんな感じ。
  ``` shell
  # portsnap auto
  # cd /usr/ports/dns/nsd
  # make config (DNSTAPオプションを有効にする)
  # make
  # make install
  ```
- この環境(多分/var/db/ports/)が残っていれば２回目以降は
  ``` shell
  # cd /usr/ports/dns/nsd
  # make reconfig
  # make
  # make deinstall reinstall
  ```
- でもついつい忘れてバイナリパッケージで上書きしちゃうので、パッケージ
  をロックしておく。
  ``` shell
  # pkg lock nsd
  ```
- かつ、config 設定を `/etc/make.conf` に書いておく。
  ``` shell
  # echo "dns_nsd_SET= DNSTAP" >> /etc/make.conf
  ```
- すると、初回の `make config` や２回目以降の `make reconfig` が
  不要になって、DNSTAP オプションが有効になる(はず）。

## 参考文献

- 以下のページを参考にしました。感謝します。
- https://bompopo.wordpress.com/2012/11/08/freebsd-optionsの設定方法/
- https://qiita.com/nanorkyo/items/a0068cafcf9112ebbb7b
