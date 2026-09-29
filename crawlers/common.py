"""共用工具：時區、輸出路徑、log、TDX OAuth 與 JSON 存檔。

所有 crawler 都 import 這個模組，避免重複程式碼。
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

# ------------------------------------------------------------
# 時區與路徑
# ------------------------------------------------------------

TAIPEI_TZ = ZoneInfo("Asia/Taipei")

# repo 根目錄（crawlers/ 的上一層），確保無論在哪個 cwd 執行都輸出到同一個地方
REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_ROOT = REPO_ROOT / "data" / "raw"

USER_AGENT = "Mozilla/5.0 (taoyuan-airport-eda crawler)"


def now_taipei() -> datetime:
    """回傳帶有 Asia/Taipei tzinfo 的當下時間。"""
    return datetime.now(TAIPEI_TZ)


def timestamp_for_filename(now: datetime) -> str:
    """檔名用時間字串，例如 2026-09-29_091700。"""
    return now.strftime("%Y-%m-%d_%H%M%S")


def month_dir(dataset: str, now: datetime) -> Path:
    """回傳（並建立）data/raw/<dataset>/YYYY-MM/，月份依 Asia/Taipei 當下時間決定。"""
    path = RAW_ROOT / dataset / now.strftime("%Y-%m")
    path.mkdir(parents=True, exist_ok=True)
    return path


def log(message: str) -> None:
    """簡單的 console log，帶台北時間戳，立即 flush 讓 GitHub Actions log 即時顯示。"""
    stamp = now_taipei().strftime("%Y-%m-%d %H:%M:%S%z")
    print(f"[{stamp}] {message}", flush=True)


# ------------------------------------------------------------
# 桃園機場 TXT 下載
# ------------------------------------------------------------

def download_txt(url: str, dest: Path, min_bytes: int, timeout: int = 30) -> int:
    """下載 TXT 並以原始 bytes 寫入 dest（不轉碼、不修改內容）。

    檔案小於 min_bytes 視為異常，直接拋出例外。回傳實際 bytes 數。
    """
    log(f"下載 {url}")
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()

    content = response.content
    size = len(content)
    log(f"HTTP {response.status_code}，取得 {size} bytes")

    if size < min_bytes:
        raise ValueError(
            f"下載到的資料量異常（{size} bytes < 門檻 {min_bytes} bytes），"
            f"可能不是正常航班資料，已中止存檔。"
        )

    with open(dest, "wb") as f:
        f.write(content)

    written = dest.stat().st_size
    if written != size:
        raise IOError(f"寫入大小不符：預期 {size} bytes，實際 {written} bytes（{dest}）")

    log(f"已儲存：{dest}（{written} bytes）")
    return written


# ------------------------------------------------------------
# TDX OAuth 與 API
# ------------------------------------------------------------

TDX_TOKEN_URL = (
    "https://tdx.transportdata.tw/"
    "auth/realms/TDXConnect/protocol/openid-connect/token"
)


def get_tdx_credentials() -> tuple[str, str]:
    """從環境變數讀取 TDX credential。缺少時給出清楚錯誤並結束。

    絕對不印出 credential 的值。
    """
    client_id = os.environ.get("TDX_CLIENT_ID", "").strip()
    client_secret = os.environ.get("TDX_CLIENT_SECRET", "").strip()

    missing = [
        name
        for name, value in (
            ("TDX_CLIENT_ID", client_id),
            ("TDX_CLIENT_SECRET", client_secret),
        )
        if not value
    ]
    if missing:
        raise SystemExit(
            "錯誤：缺少環境變數 " + ", ".join(missing) + "。\n"
            "請在 GitHub Repository Secrets 設定 TDX_CLIENT_ID / TDX_CLIENT_SECRET，\n"
            "或在本機執行前先 export（PowerShell: $env:TDX_CLIENT_ID = '...'）。"
        )
    return client_id, client_secret


def get_tdx_access_token(timeout: int = 30) -> str:
    """以 client_credentials 取得 TDX access token。"""
    client_id, client_secret = get_tdx_credentials()

    log("向 TDX 取得 access token")
    response = requests.post(
        TDX_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=timeout,
    )
    response.raise_for_status()

    body = response.json()
    token = body.get("access_token") if isinstance(body, dict) else None
    if not token:
        raise ValueError("TDX token response 中沒有 access_token 欄位")

    log("取得 access token 成功")
    return token


def tdx_get_json(url: str, token: str, timeout: int = 60):
    """呼叫 TDX API 並回傳原始 JSON（list 或 dict），不做任何清理。"""
    log(f"呼叫 TDX API：{url}")
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        params={"$format": "JSON"},
        timeout=timeout,
    )
    response.raise_for_status()

    data = response.json()
    if not isinstance(data, (list, dict)):
        raise ValueError(f"TDX API 回傳型態異常：{type(data).__name__}（預期 list 或 dict）")

    log(f"HTTP {response.status_code}，回應型態 {type(data).__name__}")
    return data


def save_json_snapshot(dest: Path, payload: dict) -> int:
    """將 snapshot（metadata + 原始 data）寫成 UTF-8 JSON，並確認檔案非空。"""
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    size = dest.stat().st_size
    if size == 0:
        raise IOError(f"寫出的 JSON 為空檔：{dest}")

    log(f"已儲存：{dest}（{size} bytes）")
    return size


def build_snapshot(now: datetime, airport: str, endpoint: str, row_count: int, data) -> dict:
    """組出最外層 snapshot metadata，data 保留完整原始 API response。"""
    return {
        "collected_at": now.isoformat(),  # 例如 2026-09-29T09:17:00.123456+08:00
        "source": "TDX",
        "airport": airport,
        "endpoint": endpoint,
        "row_count": row_count,
        "data": data,
    }


def exit_on_error(exc: BaseException) -> None:
    """統一的失敗出口：印出錯誤並以非零 exit code 結束，避免 silent failure。"""
    log(f"失敗：{type(exc).__name__}: {exc}")
    sys.exit(1)
