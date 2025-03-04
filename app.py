from flask import Flask, render_template, request, jsonify, session
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import os
import json

app = Flask(__name__)

# セッション用の秘密鍵設定（セッションを安全に使用するため）
app.secret_key = os.urandom(24)

# Google Sheets API 設定
creds_json = os.getenv("GOOGLE_CREDENTIALS")
creds_dict = json.loads(creds_json)

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
        session["user"] = "logged_in"  # ログイン状態をセッションに保存
        return jsonify({"success": True})
    else:
        return jsonify({"success": False})

# ボタンが押されたときに記録する処理
@app.route("/record", methods=["POST"])
def record():
    # セッションにユーザー情報がない場合、ログインしていないと判断
    if "user" not in session:
        return jsonify({"error": "ログインしてください！"}), 400

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
        "taikin": 8  # H列（退勤）
    }

    if action in action_map:
        sheet.update_cell(row, action_map[action], now.strftime("%H:%M"))
        
        # 出勤時間と退勤時間から労働時間（通常と深夜）を計算
        if action in ["shukkin", "taikin"]:  # 出勤または退勤時に労働時間計算
            start_time = sheet.cell(row, 3).value  # 出勤時間（C列）
            end_time = now.strftime("%H:%M")  # 退勤時間
            regular_hours, night_hours = calculate_work_hours(start_time, end_time)
            
            # I列（通常労働時間）とJ列（深夜労働時間）に出力
            sheet.update_cell(row, 9, regular_hours)  # I列（通常労働時間）
            sheet.update_cell(row, 10, night_hours)  # J列（深夜労働時間）

            # 日別の労働時間合計を計算（I6〜I36, J6〜J36に表示）
            for i in range(6, 37):
                total_regular_hours = 0
                total_night_hours = 0
                for j in range(6, 37):
                    total_regular_hours += float(sheet.cell(i, 9).value or 0)  # I列（通常労働時間）
                    total_night_hours += float(sheet.cell(i, 10).value or 0)  # J列（深夜労働時間）

                # 合計をI6〜I36、J6〜J36に反映
                sheet.update_cell(i, 9, total_regular_hours)  # I列（通常労働時間合計）
                sheet.update_cell(i, 10, total_night_hours)  # J列（深夜労働時間合計）
        
        return jsonify({"message": f"{action} を記録しました！"})
    else:
        return jsonify({"error": "無効なアクションです。"}), 400

# ログアウト処理
@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user", None)  # セッションからログイン情報を削除
    return jsonify({"message": "ログアウトしました！"})

# Webページを表示するルート
@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
