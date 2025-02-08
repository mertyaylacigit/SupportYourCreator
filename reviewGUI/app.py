from flask import Flask, render_template, jsonify, request
import os
import json

app = Flask(__name__)

# Directory to store user data
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)  # Ensure the data directory exists

def load_pending_images():
    """Load users with pending image proofs from individual JSON files."""
    pending_images = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            file_path = os.path.join(DATA_DIR, filename)
            with open(file_path, "r", encoding="utf-8") as file:
                try:
                    user_data = json.load(file)
                    if user_data.get("image_status") == "pending":
                        user_data["id"] = filename.replace(".json", "")  # Use filename as ID
                        pending_images.append(user_data)
                except json.JSONDecodeError:
                    print(f"⚠️ Skipping invalid JSON file: {filename}")
    return pending_images

def update_image_status(user_id, status):
    """Update user image status in individual JSON files."""
    file_path = os.path.join(DATA_DIR, f"{user_id}.json")
    if not os.path.exists(file_path):
        return False

    with open(file_path, "r+", encoding="utf-8") as file:
        try:
            user_data = json.load(file)
            user_data["image_status"] = status
            file.seek(0)
            json.dump(user_data, file, indent=4)
            file.truncate()
            return True
        except json.JSONDecodeError:
            print(f"⚠️ Failed to update JSON file: {user_id}.json")
            return False

@app.route("/")
def index():
    """Serve the main webpage."""
    return render_template("index.html")

@app.route("/get_images", methods=["GET"])
def get_images():
    """Return pending images as JSON."""
    images = load_pending_images()
    return jsonify(images)

@app.route("/update_status", methods=["POST"])
def update_status():
    """Handle image approval/denial."""
    data = request.json
    user_id = data.get("user_id")
    status = data.get("status")

    if update_image_status(user_id, status):
        return jsonify({"success": True, "message": f"Image marked as {status}."})
    return jsonify({"success": False, "message": "User not found!"})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
