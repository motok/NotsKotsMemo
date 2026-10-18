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

- 現状のパーティションテーブルを表示する。
  ``` shell
  # gpart show nda0 nda1 ada1 ada2
  =>        40  4000797280  nda0  GPT  (1.9T)
	    40  4000797280        - free -  (1.9T)

  =>        40  3907029088  nda1  GPT  (1.8T)
	    40  3907029088        - free -  (1.8T)

  =>       40  468862048  ada1  GPT  (224G)
	   40  468862048     1  freebsd-zfs  (224G)

  =>       40  976773088  ada2  GPT  (466G)
	   40  976773088     1  freebsd-zfs  (466G)
  ```

- 現状のパーティションテーブルを一旦破壊する。
  - 必要なデータが残っている場合は別の場所へバックアップしておくこと。
    でないと、データが失われる。
  - 手順は同じなので、ada1 の例だけを示す。以下も同じ。
    ``` shell
    # Gpart show ada1
    =>       40  468862048  ada1  GPT  (224G)
	     40  468862048     1  freebsd-zfs  (224G)

    [root@dreadnought moto]# gpart delete -i 1 ada1
    ada1p1 deleted

    # gpart show ada1
    =>       40  468862048  ada1  GPT  (224G)
	     40  468862048        - free -  (224G)

    # gpart destroy ada1
    ada1 destroyed

    # gpart show ada1
    gpart: No such geom: ada1.
    ```

- 更地にパーティションテーブルを作成する。
  ``` shell
  # gpart show ada1
  gpart: No such geom: ada1.

  # gpart create -s gpt ada1
  ada1 created

  # gpart show ada1
  =>       40  468862048  ada1  GPT  (224G)
	   40  468862048        - free -  (224G)

  # gpart add -t freebsd-zfs ada1
  ada1p1 added

  # gpart show ada1
  =>       40  468862048  ada1  GPT  (224G)
	   40  468862048     1  freebsd-zfs  (224G)  ```
  ```
  - 上では、`gpart add` でパーティションサイズを指定しなかったので、可能な
    最大サイズで作成された。サイズを指定するなら `-s 10G` のように指定することが
    できる。こうすることで、複数のパーティションを作成することができる。


- 既存のパーティションテーブルを破壊する。



