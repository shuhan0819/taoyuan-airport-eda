# Taoyuan Airport EDA

桃園國際機場（TPE）航班與機場氣象資料的課堂 EDA 專案。

本 repo 只放程式碼與 GitHub Actions workflow；所有 raw data 由排程自動抓取後上傳到 Google Drive，**不會 commit 進 GitHub**。

## Data Collection

### 資料來源與排程

| 資料 | 來源 | 頻率 | 格式 | Google Drive 位置 | 檔名 |
|---|---|---|---|---|---|
| 桃機 Passenger（客機出入境） | 桃園機場官方 `a_flight_v4.txt`（不需 API） | 每 3 小時 | TXT | `Taoyuan-Airport-EDA-Data/raw/taoyuan_passenger/YYYY-MM/` | `a_flight_v4_YYYY-MM-DD_HHMMSS.txt` |
| 桃機 Cargo（貨機出入境） | 桃園機場官方 `af_flight_v4.txt`（不需 API） | 每 3 小時 | TXT | `Taoyuan-Airport-EDA-Data/raw/taoyuan_cargo/YYYY-MM/` | `af_flight_v4_YYYY-MM-DD_HHMMSS.txt` |
| TDX FIDS（TPE 即時航班） | TDX `v2/Air/FIDS/Airport/TPE` | 每 6 小時 | JSON | `Taoyuan-Airport-EDA-Data/raw/tdx_fids/YYYY-MM/` | `tpe_fids_YYYY-MM-DD_HHMMSS.json` |
| TDX Weather（TPE 即時機場氣象 METAR） | TDX `v2/Air/METAR/Airport/TPE` | 每 2 小時 | JSON | `Taoyuan-Airport-EDA-Data/raw/weather/YYYY-MM/` | `tpe_weather_YYYY-MM-DD_HHMMSS.json` |

- 所有時間（檔名、`collected_at`、月份資料夾）皆使用 **Asia/Taipei** 時區。
- `YYYY-MM` 月份資料夾由程式依台北當下時間自動建立，不需手動建立。
- TXT 以原始 bytes 儲存，不轉碼、不修改內容。
- TDX JSON 保留完整 API response 於 `data` 欄位，最外層加上 snapshot metadata：

```json
{
  "collected_at": "2026-09-29T09:17:00.123456+08:00",
  "source": "TDX",
  "airport": "TPE",
  "endpoint": "https://tdx.transportdata.tw/api/basic/v2/Air/...",
  "row_count": 0,
  "data": []
}
```

### Google Drive 目錄結構

```
Taoyuan-Airport-EDA-Data/
└── raw/
    ├── taoyuan_passenger/
    │   └── YYYY-MM/
    ├── taoyuan_cargo/
    │   └── YYYY-MM/
    ├── tdx_fids/
    │   └── YYYY-MM/
    └── weather/
        └── YYYY-MM/
```

### GitHub Actions workflows

| Workflow | 檔案 | cron（UTC） | 內容 |
|---|---|---|---|
| Crawl Taoyuan Airport TXT | `.github/workflows/crawl_taoyuan.yml` | `17 */3 * * *` | 客機 + 貨機 TXT |
| Crawl TDX FIDS | `.github/workflows/crawl_tdx_fids.yml` | `37 */6 * * *` | TPE FIDS JSON |
| Crawl TDX Weather METAR | `.github/workflows/crawl_tdx_weather.yml` | `47 */2 * * *` | TPE METAR JSON |

每個 workflow 都支援 `workflow_dispatch`，可在 GitHub 網頁 **Actions → 選擇 workflow → Run workflow** 手動觸發測試。

每次執行的步驟：

1. checkout repository
2. 安裝 Python 3.12 與 `requirements.txt`
3. 安裝 rclone
4. 從 `RCLONE_CONFIG` secret 寫出暫時的 `~/.config/rclone/rclone.conf`
5. 執行 crawler，輸出到 runner 上的 `data/raw/<dataset>/YYYY-MM/`
6. 檢查本地檔案存在、非空
7. `rclone copy` 到對應的 Google Drive 路徑（中間資料夾自動建立）
8. `rclone check --one-way` 驗證上傳成功
9. 刪除暫時 rclone config

Raw data 不會被 `git add` / `commit` / `push`。

### 需要的 GitHub Repository Secrets

| Secret | 用途 |
|---|---|
| `RCLONE_CONFIG` | 完整的 rclone config 內容（含名為 `gdrive` 的 Google Drive remote），workflow 執行時寫成暫時檔 |
| `TDX_CLIENT_ID` | TDX 運輸資料流通服務 OAuth client id |
| `TDX_CLIENT_SECRET` | TDX OAuth client secret |

Credential 只透過 secrets / 環境變數注入，程式中不會 hard-code，log 中也不會輸出。

## 本機執行

```bash
pip install -r requirements.txt

# 桃機 TXT（不需 credential）
python crawlers/crawler_taoyuan_passenger.py
python crawlers/crawler_taoyuan_cargo.py

# TDX（需先設定環境變數）
export TDX_CLIENT_ID="..."        # PowerShell: $env:TDX_CLIENT_ID = "..."
export TDX_CLIENT_SECRET="..."
python crawlers/crawler_tdx_fids.py
python crawlers/crawler_tdx_weather.py
```

輸出會寫到 `data/raw/<dataset>/YYYY-MM/`（已被 `.gitignore` 排除）。

## 專案結構

```
.
├── .github/workflows/
│   ├── crawl_taoyuan.yml
│   ├── crawl_tdx_fids.yml
│   └── crawl_tdx_weather.yml
├── crawlers/
│   ├── common.py                    # 時區、路徑、log、TDX OAuth、存檔
│   ├── crawler_taoyuan_passenger.py
│   ├── crawler_taoyuan_cargo.py
│   ├── crawler_tdx_fids.py
│   └── crawler_tdx_weather.py
├── scripts/
│   └── upload_to_gdrive.sh          # rclone copy + check
├── requirements.txt
└── README.md
```
