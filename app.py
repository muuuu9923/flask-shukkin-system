import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 環境変数から credentials.json の内容を取得
credentials_json = os.getenv("GOOGLE_CREDENTIALS")

if credentials_json:
    creds_dict = json.loads(credentials_json)  # JSON文字列を辞書型に変換
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict)  # 認証
    client = gspread.authorize(creds)  # Googleスプレッドシートにアクセス
else:
    raise ValueError("環境変数 'GOOGLE_CREDENTIALS' が設定されていません")
