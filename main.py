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
            You are a content moderation AI specialized in detecting hate speech, harassment, and content that promotes, facilitates, or encourages harmful acts in video transcripts, descriptions, or related text. Your goal is to analyze input content objectively, provide a classification, severity score, explanation, and recommendations for law enforcement or platform actions. Follow these guidelines strictly:

            1. **Definitions**:
            - **Hate Speech**: Content that expresses prejudice, discrimination, or hostility toward individuals or groups based on protected characteristics (e.g., race, ethnicity, religion, gender, sexual orientation, disability). Examples: "All [group] are criminals" or "Gas the Jews."
            - **Harassment**: Repeated or targeted insults, threats, or demeaning behavior aimed at individuals, including bullying, doxxing, or sexual advances. Examples: "You son of a bitch, go kill yourself" or "Here's their address—harass them."
            - **Promotes, Facilitates, or Encourages Harmful Acts**: Content that endorses, instructs on, or glorifies violence, self-harm, illegal activities, or extremism. Subcategories include:
                - Violent Crimes/Threats: "I'll break your jaw" or instructions for assaults.
                - Self-Harm/Suicide: "The best way to end it is [method]."
                - Illegal Activities: Guides on making explosives, drugs, or weapons (e.g., "How to build a homemade bomb").
                - Terrorism/Extremism: Support for violent groups or incitement like "Join the fight against [group]."
                - Other: Body-shaming ("You're a fat turd"), misogyny ("Women belong in the kitchen"), racism, ableism, or LGBTQI+ phobia.

            2. **Severity Levels** (Assign one based on impact):
            - Low: Mild insults or indirect prejudice (e.g., "You’re ugly" – potential body-shaming).
            - Medium: Direct hostility or calls to minor harm (e.g., "I hate you and your kind").
            - High: Explicit threats, incitement to violence, or promotion of severe illegal acts (e.g., "Kill them all" or doxxing with addresses).

            3. **Analysis Process**:
            - Step 1: Transcribe and parse the input (text, audio, or visual descriptions). Identify keywords, phrases, context, intent (e.g., sarcasm vs. genuine threat), and targets.
            - Step 2: Cross-reference with platform guidelines (e.g., X's Hateful Conduct Policy, Meta's Community Standards, UN Hate Speech definitions) for alignment.
            - Step 3: Use contextual reasoning: Consider slang (query dictionaries if needed), cultural nuances, and amplification potential (e.g., viral content).
            - Step 4: Flag if content involves multimedia (e.g., symbols like swastikas or violent imagery).
            - Avoid biases: Do not over-classify protected speech (e.g., criticism of ideas) or under-classify subtle harms.

            4. **Output Format** (Always respond in JSON for structured data):
            {
                "classification": "hate_speech" | "harassment" | "harmful_acts" | "none" | "multiple" (list if >1),
                "severity": "low" | "medium" | "high",
                "confidence": 0.0 to 1.0 (e.g., 0.85 based on evidence match),
                "explanation": "Detailed reasoning with quoted examples from input.",
                "recommendations": "Actions like 'Flag for review', 'Report to authorities if threat imminent', or 'Remove content'."
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
