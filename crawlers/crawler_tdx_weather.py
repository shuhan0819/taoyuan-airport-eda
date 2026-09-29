"""TDX 桃園機場（TPE）即時機場氣象（METAR）crawler。

API：https://tdx.transportdata.tw/api/basic/v2/Air/METAR/Airport/TPE
    endpoint 來源：TDX 官方「航空」API swagger
    https://tdx.transportdata.tw/api-service/swagger/basic/eb87998f-2f9c-4592-8d75-c62e5b724962
    （GET /v2/Air/METAR/Airport/{IATA}，回傳 array of METAR）
    欄位：AirportID, StationID, ObservationTime, MetarText, MetarTime, WindDirection,
         WindSpeed, Visibility, Ceiling, Temperature, WeatherDescription, UpdateTime
認證：OAuth2 client_credentials，credential 只從環境變數 TDX_CLIENT_ID / TDX_CLIENT_SECRET 讀取。
輸出：data/raw/weather/YYYY-MM/tpe_weather_YYYY-MM-DD_HHMMSS.json

JSON 內容為最外層 snapshot metadata + 完整未清理的 API response（放在 "data"）。
用途：從現在開始持續保存氣象 snapshot，未來與航班資料做時間對齊。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    build_snapshot,
    exit_on_error,
    get_tdx_access_token,
    log,
    month_dir,
    now_taipei,
    save_json_snapshot,
    tdx_get_json,
    timestamp_for_filename,
)

AIRPORT = "TPE"
API_URL = f"https://tdx.transportdata.tw/api/basic/v2/Air/METAR/Airport/{AIRPORT}"
DATASET = "weather"
FILENAME_PREFIX = "tpe_weather"

# 依官方 swagger 預期會出現的欄位，缺少時只警告、不擋存檔（raw data 以保留為優先）
EXPECTED_FIELDS = (
    "AirportID",
    "StationID",
    "ObservationTime",
    "MetarText",
    "MetarTime",
    "WindDirection",
    "WindSpeed",
    "Visibility",
    "Ceiling",
    "Temperature",
    "WeatherDescription",
    "UpdateTime",
)


def validate(data) -> None:
    """檢查 response 是否為合理型態。"""
    if not isinstance(data, list):
        raise ValueError(f"METAR response 應為 list，實際為 {type(data).__name__}")
    if len(data) == 0:
        # 空 list 仍存檔，保留「當下沒有觀測資料」這個事實，但要在 log 明顯標示
        log("警告：METAR response 為空 list，仍會存檔以保留 snapshot")
        return
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"METAR response 第 {i} 筆不是 dict，結構與預期不符")

    first = data[0]
    missing = [f for f in EXPECTED_FIELDS if f not in first]
    if missing:
        log(f"警告：第一筆缺少欄位 {missing}，仍會存檔")
    if first.get("AirportID") != AIRPORT:
        log(f"警告：第一筆 AirportID 為 {first.get('AirportID')!r}，非 {AIRPORT}")
    else:
        log(
            f"觀測時間 {first.get('ObservationTime')}，"
            f"METAR：{str(first.get('MetarText', ''))[:80]}"
        )


def main() -> None:
    log(f"開始抓取 TDX {AIRPORT} 即時機場氣象（METAR）")
    now = now_taipei()

    token = get_tdx_access_token()
    data = tdx_get_json(API_URL, token)
    validate(data)

    row_count = len(data)
    log(f"觀測筆數：{row_count}")

    dest_dir = month_dir(DATASET, now)
    dest = dest_dir / f"{FILENAME_PREFIX}_{timestamp_for_filename(now)}.json"

    snapshot = build_snapshot(now, AIRPORT, API_URL, row_count, data)
    size = save_json_snapshot(dest, snapshot)

    log(f"完成：{dest}，{size} bytes")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        exit_on_error(exc)
