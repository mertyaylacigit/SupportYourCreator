import discord
from flask import Flask, render_template, jsonify, request, send_from_directory, session, redirect, url_for, send_file
import os
import json
import requests
from db_handler import load_user_data # load is synchronous. Do Not use asynchronous functions because conflict with event loop of discord bot
from config import ADMIN_PASSWORD, DISCORD_BOT_URL
import zipfile


app = Flask(__name__)
app.secret_key = ADMIN_PASSWORD

# Directory for user files
DATA_DIR = "data"
ABS_DATA_DIR = os.path.abspath(DATA_DIR)
os.makedirs(DATA_DIR, exist_ok=True)


### HELPER FUNCTIONS ###

def load_pending_images():
    """Load users with pending image proofs."""
    user_entries = []
    for file_name in os.listdir(DATA_DIR):
        if file_name.endswith(".json"):
            discord_id = file_name.split(".json")[0]
            user_data = load_user_data(discord_id)
            if user_data and user_data["images"]:
                image = user_data["images"][-1]  # the last image is the one that is pending. If there are images before they are denied
                if image.get("image_status") == "pending":
                    user_entries.append(user_data)
    return user_entries

def load_pending_videos():
    """Load users with pending video proofs."""
    video_entries = []
    for file_name in os.listdir(DATA_DIR):
        if file_name.endswith(".json"):
            discord_id = file_name.split(".json")[0]
            user_data = load_user_data(discord_id)
            if user_data and user_data["videos"]:
                video = user_data["videos"][-1]  # the last video is the one that is pending. If there are videos before they are approve/denied
                if video.get("video_status") == "pending":
                    video_entries.append(user_data)
    return video_entries





### ROUTES ###

@app.route("/")
def home():
    return "Welcome to SupportYourCreator Discord Bot that helps to connect content creator and supporters!", 200

@app.route("/download_db", methods=["GET"])
def download_db():
    """Zips the 'data/' directory and sends it as a downloadable file."""
    if not os.path.exists(DATA_DIR):
        return "Error: Data directory not found", 404

    ## Create a zip file of the 'data' directory
    #with zipfile.ZipFile("reviewGUI/zip_db.zip", 'w', zipfile.ZIP_DEFLATED) as zipf:
    #    for root, dirs, files in os.walk(DATA_DIR):
    #        for file in files:
    #            file_path = os.path.join(root, file)
    #            zipf.write(file_path, os.path.relpath(file_path, DATA_DIR))  # Keep relative path
    ## Send the zip file for download
    #return send_file("zip_db.zip", as_attachment=True)

    file_metadata = []

    for file_name in os.listdir(DATA_DIR):
        file_path = os.path.join(DATA_DIR, file_name)
        if os.path.isfile(file_path):
            file_info = {
                "file_name": file_name,
                "size_bytes": os.path.getsize(file_path),
                "modified_time": os.path.getmtime(file_path)
            }
            file_metadata.append(file_info)

    return jsonify({"files": file_metadata})
    

@app.route("/reviewer", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            session["authenticated"] = True
            return redirect(url_for("index"))
        else:
            return "❌ Falsches Passwort", 401

    if not session.get("authenticated"):
        return '''
            <form method="post">
                <label for="password">Passwort:</label>
                <input type="password" name="password" required>
                <input type="submit" value="Login">
            </form>
        '''
    return render_template("index.html")

@app.route("/get_images", methods=["GET"])
def get_images():
    """Return pending images as JSON."""
    images = load_pending_images()
    return jsonify(images)

@app.route("/get_videos", methods=["GET"])
def get_videos():
    """Return pending videos as JSON."""
    videos = load_pending_videos()
    return jsonify(videos)

@app.route("/update_image_status", methods=["POST"])
def update_image_status_route():
    """Handle image approval/denial."""
    data = request.json
    discord_id = data.get("discord_id")
    status = data.get("status")
    comment = data.get("comment")  # Optional comment for denial
    
    # ✅ Notify the Discord bot
    notify_data = {
        "discord_id": discord_id,
        "file_type": "image",
        "status": status,
        "comment": comment
    }
    try:
        response = requests.post(DISCORD_BOT_URL, json=notify_data, timeout=5)
        #print(f"✅ Notified Discord Bot: {response.text}")
        #if not response.ok:
                
    except requests.exceptions.RequestException as e:
        print(f"❌ Error notifying bot: {e}")
        
    return jsonify({"success": True, "message": f"Image for user {discord_id} marked as {status}."})




@app.route("/update_video_status", methods=["POST"])
def update_video_status_route():
    """Handle video approval/denial."""
    data = request.json
    discord_id = data.get("discord_id")
    status = data.get("status")
    comment = data.get("comment")  # Optional comment for denial
    points_added = data.get("points_added")  # Optional points added for approval

        # ✅ Notify the Discord bot
    notify_data = {
        "discord_id": discord_id,
        "file_type": "video",
        "status": status,
        "points_added": points_added,
        "comment": comment
    }
    try:
        response = requests.post(DISCORD_BOT_URL, json=notify_data, timeout=5)
        #print(f"✅ Notified Discord Bot: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error notifying bot: {e}")
        
    return jsonify({"success": True, "message": f"Video for user {discord_id} marked as {status}."})
    

@app.route("/bulk_approve", methods=["POST"])
def bulk_approve():
    """Handle bulk approval of images and notify the Discord bot."""
    data = request.json
    discord_ids = data.get("discord_ids", [])
    print(f"Bulk approving images for user IDs: {discord_ids}")

    approved_count = 0
    for discord_id in discord_ids:
        if update_image_status(discord_id, "approved"):
            approved_count += 1

            # ✅ Notify the Discord bot for each approved user
            notify_data = {
                "discord_id": discord_id,
                "file_type": "image",
                "status": "approved"
            }
            try:
                response = requests.post(DISCORD_BOT_URL, json=notify_data, timeout=5)
                #print(f"✅ Notified Discord Bot for {discord_id}: {response.text}")
            except requests.exceptions.RequestException as e:
                print(f"❌ Error notifying bot for {discord_id}: {e}")

    if approved_count > 0:
        return jsonify({"success": True, "message": f"{approved_count} images approved and notified."})
    return jsonify({"success": False, "message": "No images approved!"})

@app.route("/images/<filename>")
def serve_image(filename):
    """Serve image files from the data folder."""
    try:
        file_path = os.path.join(ABS_DATA_DIR, filename)
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
        return send_from_directory(ABS_DATA_DIR, filename)
    except Exception as e:
        return jsonify({"error": "An error occurred while serving the file"}), 500


@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')




if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)  # Start Flask app
