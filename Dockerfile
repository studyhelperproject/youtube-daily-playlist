FROM python:3.12-slim

# 出力のバッファリングを無効化（ログをリアルタイムで Cloud Logging に流す）
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードのコピー
COPY youtube_manager.py .
COPY cloud_run_daily_job.py .

# 実行
CMD ["python", "cloud_run_daily_job.py"]
