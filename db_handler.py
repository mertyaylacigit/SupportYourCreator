import json
import os
import sys
import requests
from datetime import datetime

# Define storage location for user files
DB_DIR = "data"
os.makedirs(DB_DIR, exist_ok=True)  # Ensure directory exists

# List of attributes each user entry should have
attributes_list = [
    "discord_id",
    "discord_name",
    "epic_name",
    "timestamp_epic_name",
    "images",  # List of images
    "videos",  # List of videos
    "step_state",  # [image_proof, wait, video_proof] - Tracks user progress.
    "points_assigned",
    "reacted_hand"
]

# GET

# ✅ File path helper
def get_user_file(discord_id):
    """Returns the file path for the user's data."""
    return os.path.join(DB_DIR, f"{discord_id}.json")

# ✅ Initialize user file if missing
def initialize_key(discord_id):
    """Initializes a user entry with empty attributes if not already created."""
    file_path = get_user_file(discord_id)

    if not os.path.exists(file_path):
        user_data = {attr: None for attr in attributes_list}
        user_data["discord_id"] = str(discord_id)
        user_data["images"] = []  # Initialize empty images list
        user_data["videos"] = []  # Initialize empty videos list
        user_data["step_state"] = "epic_name"  # The user's next step is to enter their Epic Games name
        user_data["points_assigned"] = discord_id
        user_data["reacted_hand"] = False
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(user_data, file, indent=4)

# ✅ Load user data/user entry
def load_user_data(discord_id):
    """Loads a user's data from their JSON file."""
    file_path = get_user_file(discord_id)

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    return None  # User file does not exist

def download_media(media_url, file_path):
    """Downloads a media file (image/video) from the given URL and saves it locally."""
    try:
        response = requests.get(media_url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Save the media file
        with open(file_path, "wb") as media_file:
            media_file.write(response.content)

        print(f"✅ Media saved at {file_path}")
        return file_path
    except requests.RequestException as e:
        print(f"❌ Failed to download media: {e}")
        return None

# END OF GET


# POST

# ✅ Save user data
def save_user_data(discord_id, data):
    """Saves user data to their individual JSON file."""
    file_path = get_user_file(discord_id)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

# ✅ Save Epic Games ID
def save_epic_name_to_database(discord_id, discord_name, epic_name):
    """Saves the Epic Games ID for a user."""
    initialize_key(discord_id)  # Ensure user file exists
    user_data = load_user_data(discord_id)  # Load current data

    user_data["epic_name"] = str(epic_name)
    user_data["discord_name"] = str(discord_name)
    user_data["timestamp_epic_name"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    user_data["step_state"] = "image_proof"  # The user's next step is to upload image proof

    save_user_data(discord_id, user_data)  # Save back to file
    print(f"✅ Saved Epic Games ID for user {discord_id}")

# ✅ Save Image Proof
def save_image_to_database(discord_id, image_url):
    """Saves the image data for a user."""
    initialize_key(discord_id)  # Ensure user file exists
    user_data = load_user_data(discord_id)  # Load current data

    # Download image from Discord's CDN
    image_path = os.path.join(DB_DIR, f"{discord_id}_{len(user_data['images']) + 1}.png")
    downloaded_image_path = download_media(image_url, image_path)

    # Add image data to the user's images list
    user_data["images"].append({
        "image_url_cdn": image_url,
        "image_path": downloaded_image_path,
        "timestamp_uploaded": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "image_status": "pending"
    })
    user_data["step_state"] = "wait"  # The user should wait for a response

    save_user_data(discord_id, user_data)  # Save back to file
    print(f"✅ Saved image proof for user {discord_id}")

# ✅ Save Video Proof
def save_video_to_database(discord_id, streamable_video_url):
    """Saves the video data for a user."""
    initialize_key(discord_id)  # Ensure user file exists
    user_data = load_user_data(discord_id)  # Load current data

    # Add video data to the user's videos list
    user_data["videos"].append({
        "streamable_video_url": streamable_video_url, # This url redirects to streamble.com and there I can watch/download the video
        "timestamp_uploaded": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "video_status": "pending"
    })
    user_data["step_state"] = "wait"  # The user should wait for a response

    save_user_data(discord_id, user_data)  # Save back to file
    print(f"✅ Saved video proof for user {discord_id}")

# --- END OF POST ---


# --- CLI Commands for Testing ---
if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "populate":
        from config import sample_image_urls, sample_video_urls
        for i in range(1, int(sys.argv[2]) + 1):
            save_epic_name_to_database(i, f"epic_name_{i}")
            #save_image_to_database(i, sample_image_urls[i % len(sample_image_urls)])
            #save_video_to_database(i, sample_video_urls[i % len(sample_video_urls)])

    elif len(sys.argv) > 1 and sys.argv[1] == "getkey":
        print(load_user_data("99998"))

    # COMMENTED SO I CANNOT ACCIDENTALY DELETE THE DATABASE
    elif len(sys.argv) > 1 and sys.argv[1] == "DELETE":
        for filename in os.listdir(DB_DIR):
            file_path = os.path.join(DB_DIR, filename)
            os.remove(file_path)
        print("✅ Delete complete!")
    else:
        print("No argument provided!")
