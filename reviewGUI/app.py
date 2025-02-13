import discord
from flask import Flask, render_template, jsonify, request, send_from_directory
import os
import json
import requests

app = Flask(__name__)

# Directory for user files
DATA_DIR = "data"
ABS_DATA_DIR = os.path.abspath(DATA_DIR)
os.makedirs(DATA_DIR, exist_ok=True)

DISCORD_BOT_URL = "http://127.0.0.1:5001/notify"  # Localhost communication

### HELPER FUNCTIONS ###

def load_pending_images():
    """Load users with pending image proofs."""
    user_entries = []
    for file_name in os.listdir(DATA_DIR):
        if file_name.endswith(".json"):
            file_path = os.path.join(DATA_DIR, file_name)
            with open(file_path, "r", encoding="utf-8") as file:
                user_data = json.load(file)
                if user_data["images"]:
                    image = user_data["images"][-1] # the last image is the one that is pending. If there are images before they are denied
                    if image.get("image_status") == "pending":
                        user_entries.append({**user_data})
                        #print(user_data)
    return user_entries

def load_pending_videos():
    """Load users with pending video proofs."""
    video_entries = []
    for file_name in os.listdir(DATA_DIR):
        if file_name.endswith(".json"):
            file_path = os.path.join(DATA_DIR, file_name)
            with open(file_path, "r", encoding="utf-8") as file:
                user_data = json.load(file)
                if user_data["videos"]:
                    video = user_data["videos"][-1] # the last video is the one that is pending. If there are videos before they are approve/denied
                    if video.get("video_status") == "pending":
                        video_entries.append({**user_data})
    return video_entries

def update_image_status(discord_id, status, comment=None):
    """Update user image status in their JSON file."""
    
    file_path = os.path.join(DATA_DIR, f"{discord_id}.json")
    if not os.path.exists(file_path):
        return False

    with open(file_path, "r+", encoding="utf-8") as file:
        user_data = json.load(file)
        if status == "approved":
            user_data["step_state"] = "video_proof"
            user_data["points_assigned"] = 1
        elif status == "denied":
            user_data["step_state"] = "image_proof"
        image = user_data["images"][-1] # the last image is the one that is pending. If there are images before they are denied
        if image.get("image_status") == "pending":
            image["image_status"] = status
            if comment:
                image["comment"] = comment
        file.seek(0)
        json.dump(user_data, file, indent=4)
        file.truncate()
    return True

def update_video_status(discord_id, status, points_added, comment=None):
    """Update user video status in their JSON file."""
    file_path = os.path.join(DATA_DIR, f"{discord_id}.json")
    if not os.path.exists(file_path):
        return False

    with open(file_path, "r+", encoding="utf-8") as file:
        user_data = json.load(file)
        user_data["step_state"] = "video_proof"
        video = user_data["videos"][-1] # the last video is the one that is pending. If there are videos before they are denied/approved
        if video.get("video_status") == "pending":
            video["video_status"] = status
            if comment:
                video["comment"] = comment
            if status == "approved":
                user_data["points_assigned"] += points_added
        file.seek(0)
        json.dump(user_data, file, indent=4)
        file.truncate()
    return True


### ROUTES ###

@app.route("/")
def index():
    """Serve the main webpage."""
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

    if update_image_status(discord_id, status, comment):
        # ✅ Notify the Discord bot
        notify_data = {
            "discord_id": discord_id,
            "file_type": "image",
            "status": status,
            "reason": comment
        }
        try:
            response = requests.post(DISCORD_BOT_URL, json=notify_data, timeout=5)
            print(f"✅ Notified Discord Bot: {response.text}")
            #if not response.ok:
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error notifying bot: {e}")

        return jsonify({"success": True, "message": f"Image for user {discord_id} marked as {status}."})

    return jsonify({"success": False, "message": "User not found!"})

@app.route("/update_video_status", methods=["POST"])
def update_video_status_route():
    """Handle video approval/denial."""
    data = request.json
    discord_id = data.get("discord_id")
    status = data.get("status")
    comment = data.get("comment")  # Optional comment for denial
    points_added = data.get("points_added")  # Optional points added for approval

    if update_video_status(discord_id, status, points_added, comment):
        # ✅ Notify the Discord bot
        notify_data = {
            "discord_id": discord_id,
            "file_type": "video",
            "status": status,
            "points_added": points_added,
            "reason": comment
        }
        try:
            response = requests.post(DISCORD_BOT_URL, json=notify_data, timeout=5)
            print(f"✅ Notified Discord Bot: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Error notifying bot: {e}")

        return jsonify({"success": True, "message": f"Video for user {discord_id} marked as {status}."})

    return jsonify({"success": False, "message": "User not found!"})

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
                print(f"✅ Notified Discord Bot for {discord_id}: {response.text}")
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



if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
