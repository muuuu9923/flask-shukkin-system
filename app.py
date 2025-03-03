from flask import Flask, render_template, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import os
import json

app = Flask(__name__)

# 環境変数から credentials.json の内容を取得
creds_json = os.getenv("GOOGLE_CREDENTIALS")
creds_dict = json.loads(creds_json)

# Google Sheets API 設定
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

SPREADSHEET_ID = "1A3wPi4iZ2PCf-WSPFqeNvWKltmwTgsZOa78OfE6M1kY"  # スプレッドシートIDを入れる
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

# ユーザーのパスワード（現段階では1人のみ）
USER_PASSWORD = "5689"  # ここにパスワードを設定

# 今日の日付を取得
def get_today_row():
    today = datetime.datetime.now().day
    return today + 5  # 1日 → 6行目, 2日 → 7行目, ...

# ログイン認証
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    password = data.get("password")

    if password == USER_PASSWORD:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False})

# ボタンが押されたときに記録する処理
@app.route("/record", methods=["POST"])
def record():
    data = request.json
    action = data["action"]
    now = datetime.datetime.now().strftime("%H:%M")
    row = get_today_row()

    # アクションに応じて記録するセルを決定
    action_map = {
        "shukkin": 3,  # C列（出勤）
        "kyukei1_start": 4,  # D列（1回目の休憩開始）
        "kyukei1_end": 5,  # E列（1回目の休憩終了）
        "kyukei2_start": 6,  # F列（2回目の休憩開始）
        "kyukei2_end": 7,  # G列（2回目の休憩終了）
        "taikin": 9  # I列（退勤）
    }

    if action in action_map:
        sheet.update_cell(row, action_map[action], now)
        return jsonify({"message": f"{action} を記録しました！"})
    else:
        return jsonify({"error": "無効なアクションです。"}), 400

# Webページを表示するルート
@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
