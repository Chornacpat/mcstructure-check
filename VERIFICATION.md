# v0.2.0 验证记录

| 样本 | 输入与来源 | 预期并实测 |
|---|---|---|
| 微软 House 1 | 国际基岩版官方示例，未压缩 v1；[样本](https://github.com/microsoft/minecraft-samples/blob/main/structure_blocks_sample_behavior_pack/structures/house1.mcstructure)，Git blob `11fcc4b456486e3d69dc7254995735d457f16b40` | 6 × 6 × 4；0 个命令方块、0 项发现，退出码 0 |
| HoloPrint 命令方块样本 | 第三方仓库未压缩 v1 测试文件；[样本](https://github.com/SuperLlama88888/holoprint/blob/6c22a674463126a676b6e7b9671312e89d38e3f5/tests/sampleStructures/command_blocks.mcstructure)，Git blob `96fe37d5d7304609e93826b419397a6d0194ffbc`。仓库未明确记录此文件的游戏导出过程。 | 11 × 3 × 7；36 个命令方块、36 条空指令提醒，退出码 1 |
| HoloPrint 压缩结构样本 | 第三方仓库压缩 v2 测试文件；[来源 PR #552](https://github.com/SuperLlama88888/holoprint/pull/552)，路径 `tests/sampleStructures/format_version_2_2.mcstructure`，Git blob `f44ff0a3cef71c804d0d7d3e8337d67f6536287d`。没有把它等同于关联 issue 的游戏导出附件。 | 13 × 8 × 7；0 个命令方块、0 项发现，退出码 0 |
| 压缩命令方块样例 | 包内 `examples/compressed-findings.mcstructure`，按 Mojang 26.60 格式生成的合成测试数据 | 3 × 2 × 2；5 个命令方块、8 项预期发现，退出码 1，与对应未压缩内容一致 |

外部样本不随本包分发。以上测试只读取文件。没有执行其中的任何命令，不代表游戏导入、服务器写入或网易版兼容性已验证。

复现：在压缩包解出目录运行 `python -m unittest discover -v`。使用 CLI 检查所下载的样本，针对外部文件先核对 Git blob SHA（`git hash-object 文件名`）。
