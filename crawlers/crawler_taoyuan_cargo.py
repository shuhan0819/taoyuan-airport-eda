"""桃園機場官方貨機出入境航班 TXT crawler。

來源：https://www.taoyuan-airport.com/uploads/flightx/af_flight_v4.txt（不需 API）
輸出：data/raw/taoyuan_cargo/YYYY-MM/af_flight_v4_YYYY-MM-DD_HHMMSS.txt
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

URL = "https://www.taoyuan-airport.com/uploads/flightx/af_flight_v4.txt"
DATASET = "taoyuan_cargo"
FILENAME_PREFIX = "af_flight_v4"

# 貨機檔近期約 32–37 KB；低於此門檻視為異常
MIN_BYTES = 5_000


def main() -> None:
    log("開始抓取桃園機場貨機航班 TXT")
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
