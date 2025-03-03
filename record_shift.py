import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# 認証情報の読み込み
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# スプレッドシートを開く（スプレッドシートIDを自分のものに変更）
SPREADSHEET_ID = "1A3wPi4iZ2PCf-WSPFqeNvWKltmwTgsZOa78OfE6M1kY"  # スプレッドシートIDを記入
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

# 今日の日付を取得（1〜31日）
today = datetime.datetime.now().day

# 今日の日付に対応する行を計算（A列の6行目から開始）
row = today + 5  # 例: 1日 → 6行目, 2日 → 7行目, 31日 → 36行目

# 現在の時刻を取得
now = datetime.datetime.now().strftime("%H:%M")

# ユーザーに入力を求める（出勤・休憩開始・休憩終了・退勤）
print("記録したいアクションを選択してください：")
print("1: 出勤, 2: 1回目休憩開始, 3: 1回目休憩終了, 4: 2回目休憩開始, 5: 2回目休憩終了, 6: 退勤")
action = input("番号を入力してください: ")

# アクションに応じてセルを更新
if action == "1":
    sheet.update_cell(row, 3, now)  # C列（出勤時間）
    print(f"出勤時間 {now} を記録しました。")
elif action == "2":
    sheet.update_cell(row, 4, now)  # D列（1回目休憩開始）
    print(f"1回目の休憩開始時間 {now} を記録しました。")
elif action == "3":
    sheet.update_cell(row, 5, now)  # E列（1回目休憩終了）
    print(f"1回目の休憩終了時間 {now} を記録しました。")
elif action == "4":
    sheet.update_cell(row, 6, now)  # F列（2回目休憩開始）
    print(f"2回目の休憩開始時間 {now} を記録しました。")
elif action == "5":
    sheet.update_cell(row, 7, now)  # G列（2回目休憩終了）
    print(f"2回目の休憩終了時間 {now} を記録しました。")
elif action == "6":
    sheet.update_cell(row, 9, now)  # I列（退勤時間）
    print(f"退勤時間 {now} を記録しました。")
else:
    print("無効な入力です。1〜6の番号を選んでください。")
