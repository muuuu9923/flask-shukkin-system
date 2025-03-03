from flask import Flask

app = Flask(__name__)  # Flask アプリのインスタンスを作成

@app.route("/")
def home():
    return "Hello, Flask is running on Render!"

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=10000)
