# 时之笛(Switch 2 重制版)Mac 原生版:越玩越慢 / 闪退 / 卡顿 的排查与解决记录

English summary: Ocarina of Time (Switch 2, title 0400486024DEC000, update v131072) built with [seedds/nxnative](https://github.com/seedds/nxnative) on a 16 GB fanless M5 MacBook Air slowed down progressively (30 fps → 8 fps after 6–10 min) and then crashed. Cause 1: three `.zs` textures in the NUP had their first 8–12 KB zeroed (the NUP's per-file SHA-256 passes because it was taken over the bad bytes), so the game's loader retried them forever after the memory pool filled. Cause 2: memory pressure (+ upstream #2277 / allocator-pool waits, fixed by `fd8188c9`). `DM_GUEST_FILE=1` plus updating to a build with the plaid/black-texture fixes gave a flat 33.3 ms for 17+ minutes. Scripts in `scripts/` detect the damaged files and check stand-in textures. **No game data is in this repository.**

> 机器:MacBook Air M5,16 GB,无风扇,macOS 27。游戏:`0400486024DEC000` v131072。构建工具:`seedds/nxnative`(MIT)。
> 本仓库只有说明和脚本,**没有任何游戏数据**(替身贴图、镜像、日志里的游戏内容都不上传)。

## 1. 症状与最终结论

| 症状 | 原因 | 处理 |
|---|---|---|
| 玩 1~2 分钟后越来越慢,30 帧掉到 8 帧,日志里 `application pool is full` 之后加载线程 `OptimizeChangeBanc` 满载 | NUP 里有 3 个 `.zs` 贴图文件**头部被写成全 0**,游戏在内存池满了之后反复尝试加载这三张图(日志里读了 5 万多次) | 做同尺寸"替身"文件原地覆盖(第 3 节) |
| 换成替身后爬藤蔓进下一个区域时闪退(退出码 139) | 第一版替身文件的**重定位表(`_RLT`)是坏的**:BNTX 头里的指针被加了两次基址 | 用头部布局一致的贴图重新构造,并用 `scripts/validate_rlt.py` 校验 |
| 修好以上后,玩 6~10 分钟仍会掉到 8~15 帧(慢动作) | 内存压力;日志里每帧等 GPU 的次数从约 9 涨到 20+(命令分配器池 8 个被用空),上游已有修复 | `DM_GUEST_FILE=1` + 更新到含 `fd8188c9` 的版本 |
| 城堡门口地面出现交叉条纹("plaid")、部分贴图变黑一帧 | 上游已修复的 bug(PR #2077、#2022、#2075) | 更新到最新 main 后重新打包 |
| 偶发紫色横条 | 上游已知,`seedds/nxnative#1821`,暂无修复 | 暂不处理 |

结果(同一路线,16 GB 机器):

| | 旧版(dbf8499) | 新版(01ec314,+ `DM_GUEST_FILE=1`) |
|---|---|---|
| p50>34 ms 的慢段 | 玩 6~10 分钟后大片出现 | 95 段里 0 段(约 17 分钟) |
| 游戏时间/真实时间 最低 | 0.42~0.51 | 0.977 |
| 游戏常驻内存 | 12 GB 以上 | 约 6 GB |
| GPU 每帧 | 22~58 ms(慢时翻倍) | 20~26 ms |

## 2. 如何发现坏文件

```bash
python -I scripts/find_damaged_zs.py <nxnative 仓库路径> <app 里的 romfs.img>
```

健康的 `.zs` 以 `28 b5 2f fd` 开头。这个脚本只读,会列出开头不是 zstd 魔数的文件。(我们的镜像里恰好是 3 个:仙女泉地板、加农舞台光照、水之神殿门的贴图。)

注意:NUP 里每个文件的 SHA-256 能通过,因为哈希是在坏数据上算的,所以**打包器不会报错**。重新下载同一份 NUP 也是一样的坏文件。

## 3. 补救:同尺寸替身

把坏文件换成**同样字节数**的有效 zstd 文件,这样不用改镜像索引,原地覆盖即可。

1. 坏文件的头 8~12 KB 为 0,丢了 zstd 帧头和第 1 个压缩块;后面的压缩块还在。zstd 的块头链可以倒着找到(从文件末尾反推)。
2. 用**另一张同格式、同解压大小**的贴图,取它的第一个 128 KB 块,重新压缩,**把 BNTX 内部的贴图名改成目标名**(名字在 0x1b8 处 u16 长度 + 字符;不改名游戏会崩)。
3. 拼上原文件的后半段压缩块,用空的 raw 块(`00 00 00`)和帧头里的 FHD 字段补齐到**原字节数**。
4. 校验:解压后 `validate_rlt.py` 必须得到 `invalid 0 duplicate 0`。尾部块的回溯引用指向被替换掉的前 128 KB,所以像素内容不完全准确,最多是那张法线图局部花,不会崩。
5. 写入 `romfs.img`(记下偏移和旧字节),再 `codesign --force --deep --sign - <app>`(约 2 分钟)。

## 4. 内存设置

`env.txt`(`~/Library/Application Support/nxnative/<id>/env.txt`)里只加一行:

```
DM_GUEST_FILE=1
```

- 作用:把游戏内存放进稀疏文件,系统需要空间时可直接写盘。游戏常驻内存从 12 GB 降到约 6 GB。磁盘剩余要足够(默认至少 10 GB,不足时不启用或退出码 87)。
- **不要**加 `DM_GUEST_FILE_PUNCH=0`:贴图是不变黑了,但又会变卡(试过)。
- 诊断开关 `DM_FSLOG`、`DM_MEMSTAT`、`DM_SVC` 会让日志很大、本身增加开销,查完要删。

## 5. 重新打包(不重新解包 26 GB 镜像)

磁盘紧时的做法:用 NUP 当输入,把**未打替身的原样镜像**用 APFS 克隆(`cp -c`,0 字节)放到 `<build>/extract/v131072/RomFS.img`,脚本会逐文件核对 SHA-256 后复用它,不再解包;构建完用 `--allow-damaged` 放行那三个坏文件,再给新 app 重新打三张替身并签名。着色器链版本变了要全部重编(42,848 个,约 1 小时 17 分),先腾出约 40 GB 峰值空间。旧 app 全程不动,当回滚点。

## 6. 脚本

- `scripts/find_damaged_zs.py`:列出镜像里头部被清零的 `.zs`。
- `scripts/validate_rlt.py`:校验 BNTX 的重定位表。
- `scripts/check_frametimes.py`:读日志,输出慢段数、GPU p50、游戏时间比例。

## 7. 教训

- 不要因为"文件数对得上"就删原始安装包。
- 日志第一行的 `build: commit` 和着色器链版本能确认你开的是不是新版。
- 同一个 title 的 app 共用存档和 env.txt,别同时开两个。
