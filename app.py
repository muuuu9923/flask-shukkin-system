from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import os
import json

app = Flask(__name__)

# セッション用の秘密鍵設定（セッションを安全に使用するため）
app.secret_key = os.urandom(24)

# セッションCookieの設定
# httpsで運用する場合は True。ローカルなど http でテストする際は False にする
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = False

# Google Sheets API 設定
creds_json = os.getenv("GOOGLE_CREDENTIALS")
if creds_json is None:
    raise ValueError("環境変数 'GOOGLE_CREDENTIALS' が設定されていません。")

creds_dict = json.loads(creds_json)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

SPREADSHEET_ID = "1A3wPi4iZ2PCf-WSPFqeNvWKltmwTgsZOa78OfE6M1kY"  # スプレッドシートIDを入れる
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

USER_PASSWORD = "5689"  # パスワード設定

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

    if is_cut_off:
        minutes = round_down_to_nearest_6(minutes)
    else:
        minutes = round_up_to_nearest_6(minutes)

    if hour >= 24:
        hour += 1

    return now.replace(minute=minutes, second=0, microsecond=0, hour=hour)

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

# 今日の出勤状況を取得
@app.route("/get_today_status", methods=["GET"])
def get_today_status():
    if "user" not in session:
        return jsonify({"error": "ログインしてください！"}), 400

    row = get_today_row()
    shukkin_time = sheet.cell(row, 3).value  # 出勤（C列）
    kyukei1_start = sheet.cell(row, 4).value  # 1回目休憩開始（D列）
    kyukei1_end = sheet.cell(row, 5).value  # 1回目休憩終了（E列）
    kyukei2_start = sheet.cell(row, 6).value  # 2回目休憩開始（F列）
    kyukei2_end = sheet.cell(row, 7).value  # 2回目休憩終了（G列）
    taikin_time = sheet.cell(row, 9).value  # 退勤（I列）

    return jsonify({
        "shukkin_time": shukkin_time,
        "kyukei1_start": kyukei1_start,
        "kyukei1_end": kyukei1_end,
        "kyukei2_start": kyukei2_start,
        "kyukei2_end": kyukei2_end,
        "taikin_time": taikin_time
    })

# ボタンが押されたときに記録する処理
@app.route("/record", methods=["POST"])
def record():
    if "user" not in session:
        return jsonify({"error": "ログインしてください！"}), 400

    data = request.json
    action = data["action"]

    now = get_rounded_time(is_cut_off=True) if action in ["shukkin", "kyukei1_start", "kyukei2_start"] else get_rounded_time(is_cut_off=False)
    row = get_today_row()

    action_map = {
        "shukkin": 3,       # 出勤  C列
        "kyukei1_start": 4, # 1回目休憩開始 D列
        "kyukei1_end": 5,   # 1回目休憩終了 E列
        "kyukei2_start": 6, # 2回目休憩開始 F列
        "kyukei2_end": 7,   # 2回目休憩終了 G列
        "taikin": 9         # 退勤  I列
    }

    if action in action_map:
        sheet.update_cell(row, action_map[action], now.strftime("%H:%M"))
        return jsonify({"message": f"{action} を記録しました！"})
    else:
        return jsonify({"error": "無効なアクションです。"}), 400

# 手動編集ページ表示
@app.route("/manual_edit", methods=["GET"])
def manual_edit():
    if "user" not in session:
        return redirect(url_for("index"))
    
    row = get_today_row()
    data = {
        "shukkin": sheet.cell(row, 3).value,
        "kyukei1_start": sheet.cell(row, 4).value,
        "kyukei1_end": sheet.cell(row, 5).value,
        "kyukei2_start": sheet.cell(row, 6).value,
        "kyukei2_end": sheet.cell(row, 7).value,
        "taikin": sheet.cell(row, 9).value
    }
    return render_template("manual_edit.html", data=data)

# 手動編集データの更新処理
@app.route("/update_manual", methods=["POST"])
def update_manual():
    if "user" not in session:
        return jsonify({"error": "ログインしてください！"}), 400

    data = request.json
    row = get_today_row()

    sheet.update_cell(row, 3, data.get("shukkin"))
    sheet.update_cell(row, 4, data.get("kyukei1_start"))
    sheet.update_cell(row, 5, data.get("kyukei1_end"))
    sheet.update_cell(row, 6, data.get("kyukei2_start"))
    sheet.update_cell(row, 7, data.get("kyukei2_end"))
    sheet.update_cell(row, 9, data.get("taikin"))

    return jsonify({"message": "データが更新されました！"})

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    # 本番環境が https の場合は SESSION_COOKIE_SECURE を True にする
    # ローカル環境でのテストは http なので、False にしないとクッキーがブロックされる可能性あり
    app.run(host="0.0.0.0", port=5000, debug=True)
