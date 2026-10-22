# FreeBSD 15 gpart/zpool/zfs

## これは何？

- たまたまいくつかの SSD や HDD を初期化することがあったので、その備忘録。
- OS は FreeBSD 15.1-RELEASE-p5
- デバイスは次の通り。nda[01] は M.2 SSD で、ada1 は SATA SSD、ada2 は SATA HDD。

  | dev  | model | capacity | interface | note |
  | ---- | ----- | -------- | --------- | ---- |
  | nda0 | Apacer AS2280P4X | 2 TB | M.2 | PCIe Gen3x4, RW: 2100/1700 MB/s |
  | nda1 | Apacer AS2280P4X | 2 TB | M.2 | 同上 |
  | ada1 | TOSHIBA THNSN9240GESG | 240 GB | SATA 3.0 | 6 Gbps |
  | ada2 | Hitachi HDT725050VLA360 | 500 GB | SATA 300 | 3 Gbps 7200 github markrpm |

## gpart でパーティションテーブルを扱う

### パーティションテーブルを表示する

- 現状のパーティションテーブルを表示する。

  ``` shell
  # gpart show nda0 nda1 ada1 ada2 
  =>        40  4000797280  nda0  GPT  (1.9T)
	    40  4000797280     1  freebsd-ufs  (1.9T)

  =>        40  3907029088  nda1  GPT  (1.8T)
	    40  3907029088     1  freebsd-ufs  (1.8T)

  =>       40  468862048  ada1  GPT  (224G)
	   40  468862048        - free -  (224G)

  gpart: No such geom: ada2.
  ```
  - nda[01], ada[01] の現状のパーティションテーブルを表示した。
    nda[01] にはそれぞれ１個づつ freebsd-ufs 型のパーティションが定義されているが、
    ada1 ではパーティションテーブルは定義してあってもパーティションはなく、
    ada2 に至っては、パーティションテーブルそのものがない状態である。
  - これらは以前に使っていた時の残骸なので、一旦全パーティションテーブルを削除して
    新たに作り直すことにする。

### パーティションテーブルを削除する

  - 必要なデータが残っている場合は別の場所へバックアップしておくこと。
    でないとデータが失われる。
  - nda0 で、パーティションを削除してからパーティションテーブルも削除するのは
    こんな感じ。
  ``` shell
  # gpart show nda0
  =>        40  4000797280  nda0  GPT  (1.9T)
	    40  4000797280     1  freebsd-ufs  (1.9T)

  # gpart delete -i 1 nda0
  nda0p1 deleted

  # gpart show nda0
  =>        40  4000797280  nda0  GPT  (1.9T)
	    40  4000797280        - free -  (1.9T)

  # gpart destroy nda0
  nda0 destroyed

  # gpart show nda0
  gpart: No such geom: nda0.
  ```
### パーティションテーブルを作成する

- 更地になった nda0 にパーティションテーブルとパーティションを作成するには、
  こんな感じ。
  ``` shell
  # gpart create -s gpt nda0
  nda0 created

  # gpart show nda0
  =>        40  4000797280  nda0  GPT  (1.9T)
	    40  4000797280        - free -  (1.9T)

  # gpart add -t freebsd-zfs -a 1m nda0
  nda0p1 added

  # gpart show nda0
  =>        40  4000797280  nda0  GPT  (1.9T)
	    40        2008        - free -  (1004K)
	  2048  4000794624     1  freebsd-zfs  (1.9T)
    4000796672         648        - free -  (324K)
  ```
  - `gpart add` に与えたオプション `-a 1m` は、作成するパーティションを
    1 MiB アラインメントに沿うようにするもの。
    最近の SSD では内部的に 4 kiB 〜 16 kiB の単位で読み書きしていて、消去の
    場合は「ブロック」(1 MiB 〜 数 MiB) の単位で消去するらしい。
    で、消去が複数ブロックに跨るとそれだけ SSD への読み書きが増えることになり、
    SSD の寿命に悪影響を及ぼすとのこと。
    なので、パーティションの境界を 1 MiB アラインメントに沿うようにしておくことで、
    なるべく消去対象ブロックを少なくする作戦であるようだ。
    上の例でもパーティションの前後に free 領域ができていてもったいない気もするが、
    これが今のベストプラクティスであるとのこと。
    既存パーティションを表示したときにはなかった "- free -" の領域に注目されたい。

- 上では、`gpart add` でパーティションサイズを指定しなかったので、可能な
  最大サイズで作成された。サイズを指定するなら `-s 10G` のように指定することが
  できる。こうすることで、複数のパーティションを作成することができる。
  ``` shell
  # gpart show ada2
  gpart: No such geom: ada2.

  # gpart create -s gpt ada2
  ada2 created

  # gpart show ada2
  =>       40  976773088  ada2  GPT  (466G)
	   40  976773088        - free -  (466G)

  # gpart add -t freebsd-ufs -a 1m -s 30G ada2
  ada2p1 added
  # gpart add -t freebsd-swap -a 1m -s 16G ada2
  ada2p2 added
  # gpart add -t freebsd-zfs -a 1m -s 130G ada2
  ada2p3 added
  # gpart add -t freebsd-zfs -a 1m -s 130G ada2
  ada2p4 added
  # gpart add -t freebsd-zfs -a 1m ada2
  ada2p5 added

  # gpart show ada2
  =>       40  976773088  ada2  GPT  (466G)
	   40       2008        - free -  (1004K)
	 2048   62914560     1  freebsd-ufs  (30G)
     62916608   33554432     2  freebsd-swap  (16G)
     96471040  272629760     3  freebsd-zfs  (130G)
    369100800  272629760     4  freebsd-zfs  (130G)
    641730560  335042560     5  freebsd-zfs  (160G)
    976773120          8        - free -  (4.0K)
  ```

## zpool で ZFS プールを扱う

### シングル構成の ZFS プールを作成する

- 単純に１個のパーティション nda0p1 に ZFS プールを作成する。
  - `zpool create` に与えるデバイス指定が nda0p1 で１番スライスを指している点に
    注意。nda0 を指定しても作成できちゃうけど、それだとパーティションテーブルと
    相互に干渉してまずいはず。

  ``` shell
  # gpart show nda0
  =>        40  4000797280  nda0  GPT  (1.9T) [CORRUPT]
	    40        2008        - free -  (1004K)
	  2048  4000794624     1  freebsd-zfs  (1.9T)
    4000796672         648        - free -  (324K)

  # zpool list
  no pools available

  # zpool create -o ashift=12 singletank nda0p1

  # zpool list
  NAME         SIZE  ALLOC   FREE  CKPOINT  EXPANDSZ   FRAG    CAP  DEDUP    HEALTH  ALTROOT
  singletank  1.86T   480K  1.86T        -         -     0%     0%  1.00x    ONLINE  -
  # zpool list -v
  NAME         SIZE  ALLOC   FREE  CKPOINT  EXPANDSZ   FRAG    CAP  DEDUP    HEALTH  ALTROOT
  singletank  1.86T   480K  1.86T        -         -     0%     0%  1.00x    ONLINE  -
    nda0p1    1.86T   480K  1.86T        -         -     0%  0.00%      -    ONLINE        -

  # zpool get ashift singletank
  NAME        PROPERTY  VALUE   SOURCE
  singletank  ashift    12      local
  ```
  - `zpool create` にオプション `-o ashift=12` を指定すると、
    このプールがセクターサイズ 4 kiB であるように設定している。
    昔は 512 kiB セクターが普通だったけど、今どきは 4 kiB かそれ以上らしい。
    LBA でもセクター番号が溢れるのでセクターサイズを大きくする必要があったはず。
  - デフォルトでは、ルート直下にプール名で、つまり、/singletank に
    このプールがマウントされる。
    これを別の場所にマウントしたい時は `zpool create` に `-m <mountpoint>`
    オプションを与えればよい。
    他にも色々と動作が変わるようなので、詳しくは zpool-create(8) の `-m` の
    項を見てほしい。
    自分しか使わないホストだったらデフォルトのままでも良いような気もするが、複数ユーザが
    使うなら権限管理が必要になって面倒だからマウントさせないというのもアリかな。
    でも、そうするとデータセット使用時には手動マウントしないとダメかも。
    面倒なので、以下ではデフォルトの動作を前提にする。

### ZFS プールを削除する

- プールを削除するのも試しておくと、こんな感じ。
  ``` shell
  # zpool list -v
  NAME         SIZE  ALLOC   FREE  CKPOINT  EXPANDSZ   FRAG    CAP  DEDUP    HEALTH  ALTROOT
  singletank  1.86T   396K  1.86T        -         -     0%     0%  1.00x    ONLINE  -
    nda0p1    1.86T   396K  1.86T        -         -     0%  0.00%      -    ONLINE        -

  # zpool destroy singletank

  # zpool list -v
  no pools available
  ```

### ストライプ構成の ZFS プールを作成する

- ２つのパーティションを使って容量が増えた(が冗長性はない)状態を作るとこんな感じ。
  いわゆる RAID0 やね。

  ``` shell
  # gpart show nda0 nda1
  =>        40  4000797280  nda0  GPT  (1.9T) [CORRUPT]
	    40        2008        - free -  (1004K)
	  2048  4000794624     1  freebsd-zfs  (1.9T)
    4000796672         648        - free -  (324K)

  =>        40  3907029088  nda1  GPT  (1.8T)
	    40        2008        - free -  (1004K)
	  2048  3907026944     1  freebsd-zfs  (1.8T)
    3907028992         136        - free -  (68K)

  # zpool create -o ashift=12 stripetank nda0p1 nda1p1

  # zpool list -v
  NAME         SIZE  ALLOC   FREE  CKPOINT  EXPANDSZ   FRAG    CAP  DEDUP    HEALTH  ALTROOT
  stripetank  3.67T   480K  3.67T        -         -     0%     0%  1.00x    ONLINE  -
    nda0p1    1.86T   176K  1.86T        -         -     0%  0.00%      -    ONLINE        -
    nda1p1    1.82T   304K  1.81T        -         -     0%  0.00%      -    ONLINE        -
  ```
  - 約1.8TBのパーティションふたつから約3.6TBのstripetankを作っている点に注意。

### ミラー構成の ZFS プールを作成する

- ２つのパーティションを使ってミラー構成のプールを作る。いわゆる RAID1。








### RAIDZ 構成の ZFS プールを作成する




