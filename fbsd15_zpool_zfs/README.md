# FreeBSD 15 gpart/zpool/zfs

## これは何？

- たまたまいくつかの SSD や HDD を初期化することがあったので、その備忘録。
- OS は FreeBSD 15.1-RELEASE-p5
- デバイスは次の通り。

  | dev  | model | capacity | interface | note |
  | ---- | ----- | -------- | --------- | ---- |
  | nda0 | Apacer AS2280P4X | 2 TB | M.2 | PCIe Gen3x4, RW: 2100/1700 MB/s |
  | nda1 | Apacer AS2280P4X | 2 TB | M.2 | PCIe Gen3x4, RW: 2100/1700 MB/s |
  | ada1 | TOSHIBA THNSN9240GESG | 240 GB | SATA 3.0 | 6 Gbps |
  | ada2 | Hitachi HDT725050VLA360 | 500 GB | SATA 300 | 3 Gbps 7200 github markrpm |


