from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/record_shift", methods=["POST"])
def record_shift():
    data = request.get_json()
    action = data.get("action")
    # ここで Google スプレッドシートにデータを記録する処理を追加
    return jsonify({"message": f"{action} を記録しました！"})

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=10000)
