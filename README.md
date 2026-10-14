# 南京气象数据可视化

爬取南京市 2023 年逐日天气数据，用 matplotlib 绘制全年 12 个月的折线图、散点图、饼图、热力图与 3D 曲面图，并以南京地图为蒙版生成天气词云。

![天气词云](结果图/wordcloud.jpg)

## 内容

| 文件 | 说明 |
| --- | --- |
| `WeatherForNanjing.ipynb` | Jupyter Notebook 完整流程（含运行输出） |
| `WeatherForNanjing.py` | 同流程的 Python 脚本版 |
| `weather.csv` | 爬取得到的逐日数据（日期、最高气温、最低气温、天气） |
| `南京地图.jpg` | 词云蒙版图片 |
| `结果图/` | 全部生成图表，按图表类型分目录 |

## 流程

1. 按月份抓取 2023 年南京逐日天气（`requests` + `lxml` + XPath），写入 `weather.csv`；
2. 按月份分组绘制折线图、散点图、饼图、热力图与 3D 曲面图（`matplotlib`）；
3. 以天气文本和南京地图蒙版生成词云（`wordcloud`）。

## 运行

需要 Python 3.9+：

```sh
pip install requests lxml numpy matplotlib wordcloud imageio
python WeatherForNanjing.py
```

脚本按相对路径读写，请保持文件在同一目录下运行；Notebook 用户请把 `南京地图.jpg` 放在工作目录。

## 数据来源

天气数据来自公开历史天气页面（lishi.tianqi.com），仅供学习与演示；重新运行脚本会重新抓取。
