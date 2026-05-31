# Python睡眠质量分析预测 睡眠质量可视化


## Env build

### Conda
```bash
conda env create -f environment.yml
conda activate sleepQualityVisualization
```

### update after git pull
```bash
conda env update -f environment.yml --prune
```


## Parts

### 数据格式
(Example source using data from my wristband.

 Format:XiaoMi Mi band 7nfc ver exported from zepp app)
Data format：

```
DATA/
├── SLEEP/
│   └── SLEEP_*.csv
│       date, deepSleepTime, shallowSleepTime, wakeTime,
│       start, stop, REMTime, naps
│
├── SLEEP_MINUTE/
│   └── SLEEP_MINUTE_*.csv
│       date, time, stage, hr, respiratory_rate
│
├── ACTIVITY/
│   └── ACTIVITY_*.csv
│       date, steps, distance, runDistance, calories
│
├── ACTIVITY_MINUTE/
│   └── ACTIVITY_MINUTE_*.csv
│       date, time, steps
│
├── ACTIVITY_STAGE/
│   └── ACTIVITY_STAGE_*.csv
│       date, start, stop, distance, calories, steps
│
├── HEARTRATE/
│   └── HEARTRATE_*.csv
│       time, heartRate
│
└── HEARTRATE_AUTO/
    └── HEARTRATE_AUTO_*.csv
        date, time, heartRate
```


### 预处理与数据导入

pandas、numpy处理，导出csv文件
File：```preprocess.py```
Output：

```
OUTPUT/
├── sleep_daily_preview.csv    # 每日睡眠汇总数据(csv format)
│
|
├── sleep_daily.parquet     # 每日睡眠汇总数据(parquet format)
|
|
└── fine/
    └── sleep_fine_*.parquet               # 每天的具体数据
```


### 2.数据分析


### 3.机器学习建模


### 4.可视化

