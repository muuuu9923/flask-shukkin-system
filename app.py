from flask import Flask, render_template, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import os
import json

app = Flask(__name__)

# セッション用の鍵（ログイン機能を削除したので特に利用しませんが、Flask起動時に設定しておく）
app.secret_key = os.urandom(24)

# Cookieの設定（ログイン機能なしのため必須ではない）
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

# スプレッドシートID
SPREADSHEET_ID = "1A3wPi4iZ2PCf-WSPFqeNvWKltmwTgsZOa78OfE6M1kY"
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

def day_to_row(day: int) -> int:
    """
    指定日(day)をスプレッドシート行に換算
    1 -> 6行目, 2 -> 7行目, ...
    """
    return day + 5

def round_down_to_nearest_6(minutes):
    return (minutes // 6) * 6

def round_up_to_nearest_6(minutes):
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

########################################
# 出勤・休憩・退勤の記録 (ログイン機能なし)
########################################
@app.route("/record", methods=["POST"])
def record():
    data = request.json
    action = data.get("action")

    # 今日の日付を取得して、該当行に記録する
    today = datetime.datetime.now().day
    row = day_to_row(today)

    now = get_rounded_time(is_cut_off=(action in ["shukkin","kyukei1_start","kyukei2_start"]))
    action_map = {
        "shukkin": 3,
        "kyukei1_start": 4,
        "kyukei1_end": 5,
        "kyukei2_start": 6,
        "kyukei2_end": 7,
        "taikin": 9
    }

    if action in action_map:
        sheet.update_cell(row, action_map[action], now.strftime("%H:%M"))
        return jsonify({"message": f"{action} を記録しました！"})
    else:
        return jsonify({"error": "無効なアクションです。"}), 400

########################################
# 手動編集ページ (日付指定可能)
########################################
@app.route("/manual_edit", methods=["GET"])
def manual_edit():
    """
    ?day=XX のクエリパラメータで編集する日を指定。
    未指定なら今日の日付を編集する。
    """
    day_str = request.args.get("day")
    if day_str is None:
        day = datetime.datetime.now().day
    else:
        day = int(day_str)

    row = day_to_row(day)
    data = {
        "day": day,
        "shukkin":        sheet.cell(row, 3).value,
        "kyukei1_start":  sheet.cell(row, 4).value,
        "kyukei1_end":    sheet.cell(row, 5).value,
        "kyukei2_start":  sheet.cell(row, 6).value,
        "kyukei2_end":    sheet.cell(row, 7).value,
        "taikin":         sheet.cell(row, 9).value
    }
    return render_template("manual_edit.html", data=data)

@app.route("/update_manual", methods=["POST"])
def update_manual():
    data = request.json
    day = data.get("day")
    if day is None:
        return jsonify({"error": "日付(day)が指定されていません"}), 400

    row = day_to_row(int(day))
    sheet.update_cell(row, 3, data.get("shukkin"))
    sheet.update_cell(row, 4, data.get("kyukei1_start"))
    sheet.update_cell(row, 5, data.get("kyukei1_end"))
    sheet.update_cell(row, 6, data.get("kyukei2_start"))
    sheet.update_cell(row, 7, data.get("kyukei2_end"))
    sheet.update_cell(row, 9, data.get("taikin"))

    return jsonify({"message": f"{day}日のデータが更新されました！"})

########################################
# index ルート
########################################
@app.route("/")
def index():
    return render_template("index.html")

########################################
# サーバ起動
########################################
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
