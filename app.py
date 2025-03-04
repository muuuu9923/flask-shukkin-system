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

def round_down_to_nearest_6(minutes):
    """現在の分を6分単位に切り捨て"""
    return (minutes // 6) * 6

def round_up_to_nearest_6(minutes):
    """現在の分を6分単位に切り上げ"""
    return ((minutes + 5) // 6) * 6

def get_rounded_time(is_cut_off=True):
    now = datetime.datetime.now()
    minutes = now.minute
    hour = now.hour

    # 出勤時間、休憩開始、休憩終了時間を計算する場合
    if is_cut_off:
        minutes = round_down_to_nearest_6(minutes)
    else:
        minutes = round_up_to_nearest_6(minutes)

    # もし24時を過ぎた場合、時間を増加させる
    if hour >= 24:
        hour += 1

    return now.replace(minute=minutes, second=0, microsecond=0, hour=hour)

def convert_minutes_to_fraction(minutes):
    """分数に変換（6分単位）"""
    return round(minutes / 6, 1)

def calculate_work_hours(start_time_str, end_time_str):
    """ 出勤時間と退勤時間から労働時間を計算（通常と深夜に分けて） """
    start_time = datetime.datetime.strptime(start_time_str, "%H:%M")
    end_time = datetime.datetime.strptime(end_time_str, "%H:%M")
    
    # 時間の差を計算
    work_duration = end_time - start_time
    
    # 時間数に換算
    total_minutes = work_duration.total_seconds() / 60  # 分に換算
    
    # 通常労働時間（22時前）
    regular_minutes = 0
    if start_time.hour < 22:
        if end_time.hour <= 22:
            regular_minutes = total_minutes
        else:
            # 22時以降の時間もあるので22時までの時間を計算
            regular_minutes = (datetime.datetime(start_time.year, start_time.month, start_time.day, 22, 0) - start_time).total_seconds() / 60
    
    # 深夜労働時間（22時以降）
    night_minutes = 0
    if end_time.hour >= 22:
        # 22時からの労働時間を計算
        if end_time.hour < 24:
            night_minutes = total_minutes
        else:
            night_minutes = (end_time - datetime.datetime(end_time.year, end_time.month, end_time.day, 22, 0)).total_seconds() / 60
    
    # 分数に変換
    regular_hours = convert_minutes_to_fraction(regular_minutes)
    night_hours = convert_minutes_to_fraction(night_minutes)
    
    return regular_hours, night_hours

# ログイン認証
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    password = data.get("password")

    if password == USER_PASSWORD:
        # ログイン成功時にユーザー情報（仮に `user_name` とする）を返します
        return jsonify({"success": True, "user": "ユーザー名"})  # 必要なユーザー情報を返す
    else:
        return jsonify({"success": False})

# ボタンが押されたときに記録する処理
@app.route("/record", methods=["POST"])
def record():
    data = request.json
    action = data["action"]
    
    # 出勤、休憩開始、休憩終了、退勤に応じて時間を計算
    if action in ["shukkin", "kyukei1_start", "kyukei2_start"]:
        now = get_rounded_time(is_cut_off=True)  # 切り捨て
    else:
        now = get_rounded_time(is_cut_off=False)  # 切り上げ
    
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
        sheet.update_cell(row, action_map[action], now.strftime("%H:%M"))
        return jsonify({"message": f"{action} を記録しました！"})
    else:
        return jsonify({"error": "無効なアクションです。"}), 400

# Webページを表示するルート
@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
