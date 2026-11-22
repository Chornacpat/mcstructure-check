# MCStructure Check

A dependency-free Python preflight checker for Minecraft Bedrock `.mcstructure` files. It reports missing commands, invalid facing, and mismatched conditional settings at structure-relative coordinates without printing command text. It never modifies the input, connects to servers, or executes commands.

**Quick start (Python 3.10+):** `python -m mcstructure_check examples/clean.mcstructure`. Use `--json` for machine-readable output. Supports uncompressed v1/v2 and the zlib-compressed v2 structure field introduced in Bedrock 26.60. See [verification notes](VERIFICATION.md) for tested inputs and limits. Licensed under [MIT](LICENSE).

## 中文说明

国际基岩版 `.mcstructure` 导入前检查器。只读取你指定的结构文件；不联网、不连接服务器、不执行命令，也不修改文件。无需第三方 Python 库。

适合导入建筑前发现三个常见问题：**指令丢失、朝向异常、条件位冲突**。报告会定位到**结构内坐标**，不会输出完整命令、原存档坐标、实体列表或源文件路径。

## 试用（Python 3.10+）

解压并在 PowerShell 或终端进入本目录。Windows 下：

```powershell
py -3 -m mcstructure_check examples/clean.mcstructure
py -3 -m mcstructure_check examples/findings.mcstructure
py -3 -m mcstructure_check examples/compressed-findings.mcstructure
py -3 -m mcstructure_check 'D:\建筑\我的结构.mcstructure' --json
```

如果没有 `py`，把 `py -3` 换成 `python` 或 `python3`。默认只打印概况和问题位置；`--json` 输出可供其他工具读取的报告，不写入磁盘。想在 PowerShell 另存时可在命令末尾加 `> report.json`。

样例为合成数据，**仅供检查器测试，请勿导入正式世界**；有问题的样例正常返回退出码 1。

| 退出码 | 含义 |
|---|---|
| 0 | 已检查的项目未发现问题，不等于可安全运行 |
| 1 | 至少发现一条错误或警告 |
| 2 | 文件无法读取、结构格式有误或超出支持范围 |

## 检查范围

- 识别普通、连锁和循环命令方块。主层检查方块实体和指令字段是否存在、类型是否正确、指令是否留空。
- 检查朝向是否为六个有效方向。检查方块的 `conditional_bit` 和实体的 `conditionalMode` 是否互相冲突；信息不齐时明确提示无法对照。曾否满足条件的 `conditionMet` 不是配置位，不参与比较。
- 位置是结构内相对坐标 `[x, y, z]`，从零开始，按 `x × Y × Z + y × Z + z` 换算，不使用方块实体保存的原世界坐标。
- 检查默认调色板。读取未压缩小端 NBT 的格式 1 和 2，以及国际基岩版 26.60 引入的格式 2（只压缩 `structure`，不是整个文件）。不支持 Java 结构文件、行为包压缩档或网易中国版适配。
- 输入和解压后数据各限 64 MiB，压缩字段限 8 MiB。解析还限制节点、嵌套和格数；较大的文件可能先触发其中一项。详细问题最多显示 10,000 条，报告保留完整问题数量。
- **不判断指令的游戏语义、跨结构链路、红石时序、权限、实际写入或服务器性能。** 第三方导入器可能重写朝向、红石位或实体字段，最终结果仍要在隔离试验世界读回。

## 回归验证

```text
python -m unittest discover -v
python -m tests.make_fixtures examples
```

v0.2.0 的压缩与未压缩样例都用同一批命令方块数据对照。另已检查微软 House 1（未压缩）、HoloPrint 的 36 个命令方块样本（未压缩，指令均为空），以及 HoloPrint 的另一份压缩 v2 样本（无命令方块）。尚未验证一份同时满足「正式版游戏直接导出、采用压缩格式、含命令方块」的文件。详见 `VERIFICATION.md`。

格式参考：[Microsoft 26.50 格式 2 说明](https://learn.microsoft.com/en-us/minecraft/creator/documents/update1.26.50?view=minecraft-bedrock-stable)、[Mojang 26.60 压缩格式说明](https://feedback.minecraft.net/hc/en-us/articles/49852828563853-Minecraft-Bedrock-Edition-26-60-Changelog)、[Bedrock Wiki 的 .mcstructure 格式](https://wiki.bedrock.dev/nbt/mcstructure)。包内样例均为合成数据。第三方样本仅供独立验证，不随本项目分发。
