from flask import Flask, request, jsonify, render_template
import os
import tempfile
from google import generativeai as genai

app = Flask(__name__)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = "gemini-2.0-flash"

@app.route("/")
def index():
    return render_template("index.html")

def upload_video_for_gemini(video_path):
    video_file = genai.upload_file(video_path)
    while video_file.state.name == "PROCESSING":
        import time
        time.sleep(5)
        video_file = genai.get_file(video_file.name)
    if video_file.state.name == "FAILED":
        raise RuntimeError("Video upload failed")
    return video_file

@app.route("/analyze", methods=["POST"])
def analyze_video():
    if "video" not in request.files:
        return jsonify({"error": "no video file"}), 400

    video = request.files["video"]
    tmp_dir = tempfile.mkdtemp()
    video_path = os.path.join(tmp_dir, video.filename)
    video.save(video_path)

    try:
        video_file = upload_video_for_gemini(video_path)
        prompt = """
            You are a hate speech detector. Analyze the following video transcript/text.  

            - If it contains hate speech (insults, threats, provocation) against a group or individual in TNI (Tentara Nasional Indonesia), set "hatespeech" to "YES". Otherwise, "NO".  
            - Provide a short explanation in "conclusion".  
            - Return only a JSON object in this exact format:  
            
            {
                "hatespeech": <boolean>,
                "conclusion": <string>
            }

            Use Bahasa Indonesia language.
            Do NOT add any extra text, labels, or sentences outside the JSON.  
        """

        response = genai.GenerativeModel(MODEL_NAME).generate_content(
            [video_file, prompt],
            request_options={"timeout": 500}
        )
        print(response.text)
        return jsonify({"result": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            os.remove(video_path)
        except:
            pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
