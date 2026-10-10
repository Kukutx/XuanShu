# 出生时间、经度与时制

- `clock`：以出生地的当地民用钟表时间分时辰，默认。
- `mean_solar`：当地平太阳时 `UTC + 东经度 × 4 分钟/度`。
- `apparent_solar`：当地真太阳时 `平太阳时 + 均时差`（`Swiss Ephemeris swe.time_equ`，LAT−LMT）。
- 天文节气始终用**原始出生 UTC 瞬间**计算；经度修正只改变传统日期、时辰判定与紫微采用的当地历日。
- 经度东正西负。仅提供经度，没有出生地自动定位或地理数据库。纬度字段目前不参与计算。
- 夏令时/历史时区由 IANA `zoneinfo` 解释；不存在的民用钟点拒绝，重叠钟点要求显式 UTC offset。
- 节气附近、日界、闰月、出生时刻不确定都可能改变命盘。请对照原始资料，不要把这当作可预测人生结果的方法。

## 可核验依据

Swiss Ephemeris Programming Interface §8.4 `swe_time_equ`（E=LAT−LMT）。
https://www.astro.com/ftp/swisseph/doc/swephprg.2.10.htm
