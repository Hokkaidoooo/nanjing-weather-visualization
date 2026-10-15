# 优化验证记录

日期：2026-10-15。

| 项目 | 状态 | 证据 |
| --- | --- | --- |
| WX-01 | 完成 | GB18030 原 CSV 离线读取，365 个唯一日期、无缺日、最高温不低于最低温；缺列/重复/缺日/未知日期/非法温度均带行和字段错误 |
| WX-02 | 离线部分完成 | HTML 解析与 HTTP 获取分离；空页面、结构变化、缺日期、失败月份、超时重试上限、404 不重试和失败不写 CSV 的测试通过；在线站点兼容性另行验证 |
| WX-03 | 完成 | 实际生成 61 图，检查全部月份；散点无无意义色条，热力图横轴为日期，三维轴为日期/最高温/最低温，词云完整类别频数合计 365 天 |
| WX-04 | 完成 | 脚本和 Notebook 均调用 `run_offline`；实际执行 Notebook，与脚本的全部 61 张 PNG 校验值一致 |

## 实际执行与结果

```powershell
python -B -m unittest discover -s tests -v
python -B WeatherForNanjing.py plot --input weather.csv --encoding gb18030 --year 2023 --font C:\Windows\Fonts\simhei.ttf --output outputs\verified-20261015
python -B tools\verify_notebook.py --output .qa-notebook-render-20261015 --reference outputs\verified-20261015
python -B tools\record_preserved_files.py --verify
```

23 项测试通过；网络单测使用明确标识的人工 HTML 夹具与故障响应。另做一次真实源站探测：`robots.txt` 重定向为 HTTP 200 的 HTML 错误页，未取得有效规则；2023 年 2 月页面请求在 15 秒后读取超时，按最多 1 次尝试明确失败。没有取得真实月度 HTML，也没有生成或覆盖年度 CSV；[源站探测记录](network-probe.json)保存限制。成功读取原始 CSV、实际绘图和实际执行 Jupyter kernel 是独立的真实验证。

脚本生成五类月图各 12 张及年度词云，共 61 张。所有 PNG 都能解码，尺寸达到正常图表要求且不是空白。[manifest.json](../outputs/verified-20261015/manifest.json)记录每张图片的 SHA-256、尺寸、字体校验值、参数和依赖版本。[Notebook 验证](notebook-verification.json)记录实际执行及 61 张一致结果。

视觉检查包含全部五组月图缩略图、三维图与年度词云的原图。发现 31 天月份的 30/31 日刻度过近后，保留末日并移除过近的 30 日刻度；词云改用深色文字提高白底对比；三维散点关闭深度透明度，保持色条对应真实温差。字体检查拒绝缺字，生成时缺字警告会成为明确错误。

验证环境：Windows 10，Python 3.10.9；NumPy 2.2.6、Matplotlib 3.10.9、Pillow 11.3.0、wordcloud 1.9.3、requests 2.34.2、lxml 4.9.1。Notebook 使用 nbformat 5.7.0、nbclient 0.5.13、ipykernel 6.19.2。使用现有 Anaconda 环境，没有安装新依赖；未宣称已在全新环境复跑。

## 数据与边界

Pyflakes、Python 语法检查和 `git diff --check` 通过。项目没有独立打包步骤，已实际执行脚本和 Notebook。64 个历史文件最终逐项哈希核验通过。CSV 和原 Notebook 归档设为 Git `-text`，保留原始字节，避免换行转换使校验值在检出后变化。

- 原 CSV 为 GB18030、日期为 `YYYY/M/D`；采集新文件为 UTF-8、日期为 `YYYY-MM-DD`。内部统一使用日期对象和整数摄氏度。
- 全年 50 个完整天气类别，包括组合天气；按日类别计数，总和为 365，没有把跨日期字符串拼成词。
- 绘图命令必须指定输入、字体、新输出目录；采集是独立的 `collect` 命令，超时与最多尝试次数可配置，重试日志可见。
- 所有月份通过验证后才写新的年度 CSV；目标存在会失败，不覆盖原数据。绘图失败不会产生 `status=complete` 的 manifest。
- `tests/fixtures/february-minimal.html` 为人工构造的离线解析契约，不是站点实时 HTML 快照。本轮未重新采集全年，在线源和访问规则仍需在实际采集前核验。

## 保留材料与清理

[preserved-files.json](preserved-files.json)记录 64 个历史文件的 SHA-256：原 CSV、完整原 Notebook 归档、原始图片。原 Notebook 的内容和已有输出逐字节保存为 `archive/WeatherForNanjing.original.ipynb`；活动 Notebook 只保留参数、共享流程调用和结果说明。

临时联系图与 Notebook 比较目录的清理命令被自动策略拒绝，目录仍保留；交付保留 `outputs/verified-20261015/` 的 61 张新图、manifest、共享代码、测试和验证文档。历史数据和图片的原始字节保持不变。
## 本机清理实际结果

真实源站探测的中间 JSON 已转存为 `docs\network-probe.json`，原中间文件 `tests\fixtures\site-202302.json` 已删除。以下删除目标均由本轮创建并核验路径，但自动审批策略在启动 PowerShell 前返回 `blocked by policy`，这些删除实际未执行；没有换工具、路径或权限重试。

| 被拒绝命令涉及的绝对路径 | 文件数 | 字节数 |
| --- | ---: | ---: |
| `D:\桌面\GitHub展示整理\nanjing-weather-visualization\.qa-notebook-render-20261015` | 62 | 5563627 |
| `D:\桌面\GitHub展示整理\nanjing-weather-visualization\.qa-contact-sheets-20261015` | 5 | 2241722 |
| `D:\桌面\GitHub展示整理\nanjing-weather-visualization\.qa-render-v2-20261015` | 62 | 5482338 |
| `D:\桌面\GitHub展示整理\nanjing-weather-visualization\.qa-notebook-render-v2-20261015` | 62 | 5482338 |
| `D:\桌面\GitHub展示整理\nanjing-weather-visualization\.qa-notebook-verification-v2.json` | 1 | 383 |

另有 Notebook 执行生成的 `D:\桌面\GitHub展示整理\nanjing-weather-visualization\nanjing_weather\__pycache__`，包含 `data.cpython-310.pyc`、`plots.cpython-310.pyc`、`__init__.cpython-310.pyc`，合计 15681 字节；未尝试删除。以上临时文件和字节码均被 Git 忽略，正式结果只使用 `outputs/verified-20261015/`。
