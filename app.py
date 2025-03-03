from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/record_shift", methods=["POST"])
def record_shift():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request, no JSON received"}), 400

        action = data.get("action")
        if not action:
            return jsonify({"error": "Invalid request, 'action' is required"}), 400

        # ここで Google スプレッドシートにデータを記録する処理を追加
        print(f"記録: {action}")  # デバッグ用

        return jsonify({"message": f"{action} を記録しました！"})

    except Exception as e:
        print(f"エラー発生: {str(e)}")
        return jsonify({"error": "サーバーエラーが発生しました"}), 500

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=10000)
