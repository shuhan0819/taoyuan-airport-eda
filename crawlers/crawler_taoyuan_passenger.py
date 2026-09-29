"""桃園機場官方客機出入境航班 TXT crawler。

來源：https://www.taoyuan-airport.com/uploads/flightx/a_flight_v4.txt（不需 API）
輸出：data/raw/taoyuan_passenger/YYYY-MM/a_flight_v4_YYYY-MM-DD_HHMMSS.txt
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    download_txt,
    exit_on_error,
    log,
    month_dir,
    now_taipei,
    timestamp_for_filename,
)

URL = "https://www.taoyuan-airport.com/uploads/flightx/a_flight_v4.txt"
DATASET = "taoyuan_passenger"
FILENAME_PREFIX = "a_flight_v4"

# 客機檔近期約 550 KB；低於此門檻視為異常（例如錯誤頁、空檔）
MIN_BYTES = 100_000


def main() -> None:
    log("開始抓取桃園機場客機航班 TXT")
    now = now_taipei()

    dest_dir = month_dir(DATASET, now)
    dest = dest_dir / f"{FILENAME_PREFIX}_{timestamp_for_filename(now)}.txt"

    size = download_txt(URL, dest, MIN_BYTES)

    log(f"完成：{dest}，{size} bytes")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        exit_on_error(exc)
