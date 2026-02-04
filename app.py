"""""""""
import os
import json
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from google import genai

# ----------------------
# Flask setup
# ----------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"  # for flash messages

UPLOAD_FOLDER = "uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

UPLOADS_JSON = "uploads.json"

# Folder for gallery photos
GALLERY_FOLDER = os.path.join("static", "team_photos")
os.makedirs(GALLERY_FOLDER, exist_ok=True)

# ----------------------
# Gemini AI setup
# ----------------------
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not set!")

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-3-flash-preview"  # use "gemini-3-flash" when stable

def generate_gemini_summary(artifact_name):
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=f"Give a short interesting historical fact about the artifact '{artifact_name}' including its location or culture."
        )
        return response.text.strip()
    except Exception as e:
        print("Gemini API error:", e)
        return "AI summary unavailable."

# ----------------------
# JSON helpers
# ----------------------
def load_uploads():
    if os.path.exists(UPLOADS_JSON):
        with open(UPLOADS_JSON, "r") as f:
            return json.load(f)
    return []

def save_uploads(artifacts):
    with open(UPLOADS_JSON, "w") as f:
        json.dump(artifacts, f, indent=4)

# ----------------------
# Routes
# ----------------------
@app.route("/")
def home():
    return render_template("index.html")

# ----------------------
# Upload artifact with name & description
# ----------------------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    artifacts = load_uploads()

    if request.method == "POST":
        file = request.files.get("file")
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if file and file.filename != "" and name:
            # Save file
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(file_path)

            try:
                prompt = (
                    f"Give a short, interesting historical fact about the artifact "
                    f"'{name}', including its location or culture."
                )

                response = client.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents=[prompt]
                )

                print("Gemini response (upload):", response)  # DEBUG

                summary = getattr(response, "text", None)
                if not summary:
                    summary = "AI summary unavailable."

            except Exception as e:
                print("Gemini API error (upload):", e)
                summary = "AI summary unavailable."

            # Save artifact
            artifacts.append({
                "name": name,
                "description": description,
                "filename": file.filename,
                "summary": summary
            })

            save_uploads(artifacts)

        return redirect(url_for("upload"))

    return render_template("upload.html", uploads=artifacts)

# ----------------------
# Upload image only + AI identification
# ----------------------
@app.route("/upload-image-only", methods=["GET", "POST"])
def upload_image_only():
    artifacts = load_uploads()

    if request.method == "POST":
        file = request.files.get("file")
        description = request.form.get("description", "")

        if file and file.filename != "":
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(file_path)

            # Upload to Gemini and generate AI summary
            try:
                uploaded_file = client.files.upload(file=file_path)
                prompt = "Identify this historical artifact and provide a short, interesting historical fact including its location or culture."
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[uploaded_file, prompt]
                )
                summary = response.text.strip() if response.text else "AI summary unavailable."
            except Exception as e:
                print("Gemini API error:", e)
                summary = "AI summary unavailable."

            guessed_name = summary.split('\n')[0] if summary else "Unknown Artifact"

            artifacts.append({
                "name": guessed_name,
                "description": description,
                "filename": file.filename,
                "summary": summary,
                "image_only": True
            })
            save_uploads(artifacts)

        return redirect(url_for("upload_image_only"))

    image_only_artifacts = [a for a in artifacts if a.get("image_only")]
    return render_template("upload_image_only.html", uploads=image_only_artifacts)

# ----------------------
# Serve uploaded artifacts
# ----------------------
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ----------------------
# Delete artifact
# ----------------------
@app.route("/delete/<filename>", methods=["POST"])
def delete_artifact(filename):
    artifacts = load_uploads()
    artifacts = [a for a in artifacts if a["filename"] != filename]
    save_uploads(artifacts)

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    return redirect(url_for("upload"))

# ----------------------
# AI model info page
# ----------------------
@app.route("/model")
def model():
    return render_template("model.html")

# ----------------------
# Gallery page (with upload)
# ----------------------
@app.route("/gallery", methods=["GET", "POST"])
def gallery():
    if request.method == "POST":
        file = request.files.get("file")
        if file and file.filename != "":
            save_path = os.path.join(GALLERY_FOLDER, file.filename)
            file.save(save_path)
            flash(f"Uploaded {file.filename} successfully!", "success")
            return redirect(url_for("gallery"))
        else:
            flash("No file selected.", "error")
            return redirect(url_for("gallery"))

    photos = [f for f in os.listdir(GALLERY_FOLDER) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    photos.sort()
    return render_template("gallery.html", photos=photos)

VIDEOS_JSON = "videos.json"

def load_videos():
    if os.path.exists(VIDEOS_JSON):
        with open(VIDEOS_JSON, "r") as f:
            return json.load(f)
    return []

def save_videos(videos):
    with open(VIDEOS_JSON, "w") as f:
        json.dump(videos, f, indent=4)

@app.route("/videos", methods=["GET", "POST"])
def videos():
    videos = load_videos()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        url = request.form.get("url", "").strip()

        if title and url:
            # Convert normal YouTube link → embed link
            if "watch?v=" in url:
                video_id = url.split("watch?v=")[1].split("&")[0]
            elif "youtu.be/" in url:
                video_id = url.split("youtu.be/")[1].split("?")[0]
            else:
                video_id = None

            if video_id:
                embed_url = f"https://www.youtube.com/embed/{video_id}"

                videos.append({
                    "title": title,
                    "embed_url": embed_url
                })
                save_videos(videos)

        return redirect(url_for("videos"))

    return render_template("videos.html", videos=videos)


# ----------------------
# Run app
# ----------------------
if __name__ == "__main__":
    print("Gemini client ready:", client is not None)
    app.run(debug=True) 
    """
import os
import json
from flask import (
    Flask, render_template, request,
    redirect, url_for, send_from_directory, flash
)

from google import genai

# ----------------------
# Flask setup
# ----------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
GALLERY_FOLDER = os.path.join(BASE_DIR, "static", "team_photos")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GALLERY_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

UPLOADS_JSON = os.path.join(BASE_DIR, "uploads.json")
VIDEOS_JSON = os.path.join(BASE_DIR, "videos.json")

# ----------------------
# Gemini AI setup (Cloud-safe)
# ----------------------
api_key = os.getenv("GEMINI_API_KEY")
client = None
MODEL_NAME = "gemini-3-flash-preview"

if api_key:
    try:
        client = genai.Client(api_key=api_key)
        print("Gemini client initialized")
    except Exception as e:
        print("Failed to initialize Gemini:", e)
else:
    print("WARNING: GEMINI_API_KEY not set — AI features disabled")

# ----------------------
# JSON helpers
# ----------------------
def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

# ----------------------
# Gemini helpers
# ----------------------
def generate_text(prompt):
    if not client:
        return "AI summary unavailable."

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        return response.text.strip() if response.text else "AI summary unavailable."
    except Exception as e:
        print("Gemini error:", e)
        return "AI summary unavailable."

# ----------------------
# Routes
# ----------------------
@app.route("/")
def home():
    return render_template("index.html")

# ----------------------
# Upload artifact
# ----------------------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    artifacts = load_json(UPLOADS_JSON)

    if request.method == "POST":
        file = request.files.get("file")
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()

        if file and file.filename and name:
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)

            summary = generate_text(
                f"Give a short, interesting historical fact about the artifact "
                f"'{name}', including its location or culture."
            )

            artifacts.append({
                "name": name,
                "description": description,
                "filename": file.filename,
                "summary": summary
            })

            save_json(UPLOADS_JSON, artifacts)

        return redirect(url_for("upload"))

    return render_template("upload.html", uploads=artifacts)

# ----------------------
# Upload image-only artifact
# ----------------------
@app.route("/upload-image-only", methods=["GET", "POST"])
def upload_image_only():
    artifacts = load_json(UPLOADS_JSON)

    if request.method == "POST":
        file = request.files.get("file")
        description = request.form.get("description", "")

        if file and file.filename:
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)

            summary = "AI summary unavailable."
            guessed_name = "Unknown Artifact"

            if client:
                try:
                    uploaded_file = client.files.upload(file=file_path)
                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=[
                            uploaded_file,
                            "Identify this historical artifact and provide a short historical fact."
                        ]
                    )
                    if response.text:
                        summary = response.text.strip()
                        guessed_name = summary.split("\n")[0]
                except Exception as e:
                    print("Gemini image error:", e)

            artifacts.append({
                "name": guessed_name,
                "description": description,
                "filename": file.filename,
                "summary": summary,
                "image_only": True
            })

            save_json(UPLOADS_JSON, artifacts)

        return redirect(url_for("upload_image_only"))

    image_only = [a for a in artifacts if a.get("image_only")]
    return render_template("upload_image_only.html", uploads=image_only)

# ----------------------
# Serve uploaded files
# ----------------------
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ----------------------
# Delete artifact
# ----------------------
@app.route("/delete/<filename>", methods=["POST"])
def delete_artifact(filename):
    artifacts = load_json(UPLOADS_JSON)
    artifacts = [a for a in artifacts if a["filename"] != filename]
    save_json(UPLOADS_JSON, artifacts)

    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    return redirect(url_for("upload"))

# ----------------------
# Model info
# ----------------------
@app.route("/model")
def model():
    return render_template("model.html")

# ----------------------
# Gallery
# ----------------------
@app.route("/gallery", methods=["GET", "POST"])
def gallery():
    if request.method == "POST":
        file = request.files.get("file")
        if file and file.filename:
            save_path = os.path.join(GALLERY_FOLDER, file.filename)
            file.save(save_path)
            flash(f"Uploaded {file.filename}", "success")
        else:
            flash("No file selected.", "error")

        return redirect(url_for("gallery"))

    photos = sorted(
        f for f in os.listdir(GALLERY_FOLDER)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    )

    return render_template("gallery.html", photos=photos)

# ----------------------
# Videos
# ----------------------
@app.route("/videos", methods=["GET", "POST"])
def videos():
    videos = load_json(VIDEOS_JSON)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        url = request.form.get("url", "").strip()

        if title and url:
            video_id = None
            if "watch?v=" in url:
                video_id = url.split("watch?v=")[1].split("&")[0]
            elif "youtu.be/" in url:
                video_id = url.split("youtu.be/")[1].split("?")[0]

            if video_id:
                videos.append({
                    "title": title,
                    "embed_url": f"https://www.youtube.com/embed/{video_id}"
                })
                save_json(VIDEOS_JSON, videos)

        return redirect(url_for("videos"))

    return render_template("videos.html", videos=videos)

# ----------------------
# Entry point (Cloud Run compatible)
# ----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
