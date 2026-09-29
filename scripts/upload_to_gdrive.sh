#!/usr/bin/env bash
# 把本次 crawler 產出的月份資料夾上傳到 Google Drive，並驗證傳輸成功。
#
# 用法：bash scripts/upload_to_gdrive.sh <dataset>
#   dataset ∈ taoyuan_passenger | taoyuan_cargo | tdx_fids | weather
#
# 本地來源：data/raw/<dataset>/YYYY-MM/
# 遠端目的：gdrive:Taoyuan-Airport-EDA-Data/raw/<dataset>/YYYY-MM/
#
# 注意：
# - rclone config 由 workflow 事先寫入 ~/.config/rclone/rclone.conf，本腳本不處理 secret。
# - 本腳本只印路徑與檔名，絕不印 config 內容或 token。
# - GitHub Actions runner 上本地月份資料夾只有本次抓到的檔案，
#   因此 copy / check 只涉及新檔，不會動到 Google Drive 上既有檔案。

set -euo pipefail

DATASET="${1:-}"
if [[ -z "$DATASET" ]]; then
  echo "錯誤：請指定 dataset（taoyuan_passenger | taoyuan_cargo | tdx_fids | weather）" >&2
  exit 1
fi

case "$DATASET" in
  taoyuan_passenger|taoyuan_cargo|tdx_fids|weather) ;;
  *)
    echo "錯誤：未知的 dataset：$DATASET" >&2
    exit 1
    ;;
esac

REMOTE_NAME="gdrive"
REMOTE_ROOT="${REMOTE_NAME}:Taoyuan-Airport-EDA-Data"

# 月份依 Asia/Taipei 當下時間決定，與 Python crawler 的 month_dir() 一致
MONTH="$(TZ=Asia/Taipei date +%Y-%m)"

LOCAL_DIR="data/raw/${DATASET}/${MONTH}"
REMOTE_DIR="${REMOTE_ROOT}/raw/${DATASET}/${MONTH}"

echo "== dataset : ${DATASET}"
echo "== month   : ${MONTH} (Asia/Taipei)"
echo "== local   : ${LOCAL_DIR}"
echo "== remote  : ${REMOTE_DIR}"

# ---- 1. 確認本地檔案存在且非空 ----
if [[ ! -d "$LOCAL_DIR" ]]; then
  echo "錯誤：本地資料夾不存在：$LOCAL_DIR（crawler 可能沒有成功產出檔案）" >&2
  exit 1
fi

FILE_COUNT="$(find "$LOCAL_DIR" -type f | wc -l | tr -d ' ')"
if [[ "$FILE_COUNT" -eq 0 ]]; then
  echo "錯誤：本地資料夾沒有任何檔案：$LOCAL_DIR" >&2
  exit 1
fi

echo "== 本地檔案（${FILE_COUNT} 個）："
ls -la "$LOCAL_DIR"

EMPTY_COUNT="$(find "$LOCAL_DIR" -type f -size 0 | wc -l | tr -d ' ')"
if [[ "$EMPTY_COUNT" -ne 0 ]]; then
  echo "錯誤：發現 ${EMPTY_COUNT} 個空檔，拒絕上傳" >&2
  exit 1
fi

# ---- 2. 確認 rclone 與 remote 可用（只顯示 remote 名稱，不顯示 config 內容）----
if ! rclone listremotes | grep -qx "${REMOTE_NAME}:"; then
  echo "錯誤：rclone 找不到名為 ${REMOTE_NAME} 的 remote，請檢查 RCLONE_CONFIG secret" >&2
  exit 1
fi

# ---- 3. 上傳（rclone copy 會自動建立不存在的中間資料夾）----
echo "== 開始上傳"
rclone copy "$LOCAL_DIR" "$REMOTE_DIR" \
  --create-empty-src-dirs \
  --transfers 4 \
  --retries 3 \
  --low-level-retries 10 \
  --stats-one-line \
  -v

# ---- 4. 驗證：本地每個檔案都必須在遠端存在且大小/hash 相符 ----
echo "== 驗證上傳結果（rclone check --one-way）"
rclone check "$LOCAL_DIR" "$REMOTE_DIR" --one-way --size-only

echo "== 遠端目前檔案（最新 5 個）："
rclone lsl "$REMOTE_DIR" | sort -k2,3 | tail -n 5

echo "== 上傳完成：${REMOTE_DIR}"
