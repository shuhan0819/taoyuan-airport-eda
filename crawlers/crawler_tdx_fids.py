"""TDX 桃園機場（TPE）即時 FIDS crawler。

API：https://tdx.transportdata.tw/api/basic/v2/Air/FIDS/Airport/TPE
認證：OAuth2 client_credentials，credential 只從環境變數 TDX_CLIENT_ID / TDX_CLIENT_SECRET 讀取。
輸出：data/raw/tdx_fids/YYYY-MM/tpe_fids_YYYY-MM-DD_HHMMSS.json

JSON 內容為最外層 snapshot metadata + 完整未清理的 API response（放在 "data"）。
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
API_URL = f"https://tdx.transportdata.tw/api/basic/v2/Air/FIDS/Airport/{AIRPORT}"
DATASET = "tdx_fids"
FILENAME_PREFIX = "tpe_fids"


def count_rows(data) -> int:
    """計算航班筆數。

    TDX FIDS/Airport 回傳形如 [{"AirportID": "TPE", "FIDSDeparture": [...], "FIDSArrival": [...]}]，
    這裡把所有 FIDSDeparture + FIDSArrival 的筆數加總；若結構不同則退回 len(data)。
    """
    if not isinstance(data, list):
        return 0
    total = 0
    matched = False
    for item in data:
        if isinstance(item, dict):
            for key in ("FIDSDeparture", "FIDSArrival"):
                rows = item.get(key)
                if isinstance(rows, list):
                    total += len(rows)
                    matched = True
    return total if matched else len(data)


def validate(data) -> None:
    """檢查 response 是否為合理型態，不合理就直接拋錯。"""
    if not isinstance(data, list):
        raise ValueError(f"FIDS response 應為 list，實際為 {type(data).__name__}")
    if len(data) == 0:
        raise ValueError("FIDS response 為空 list，疑似 API 異常，已中止存檔")
    first = data[0]
    if not isinstance(first, dict) or "AirportID" not in first:
        raise ValueError("FIDS response 第一筆缺少 AirportID，結構與預期不符")
    if first.get("AirportID") != AIRPORT:
        log(f"警告：第一筆 AirportID 為 {first.get('AirportID')!r}，非 {AIRPORT}")


def main() -> None:
    log(f"開始抓取 TDX {AIRPORT} 即時 FIDS")
    now = now_taipei()

    token = get_tdx_access_token()
    data = tdx_get_json(API_URL, token)
    validate(data)

    row_count = count_rows(data)
    log(f"航班筆數（Departure + Arrival）：{row_count}")

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
