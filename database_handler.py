import json
import os
import sys
from datetime import datetime

from discord import file

# Define storage location for user files
DB_DIR = "data"
os.makedirs(DB_DIR, exist_ok=True)  # Ensure directory exists

# List of attributes each user entry should have
attributes_list = [
    "epic_name",
    "image_url",
    "timestamp_epic_name",
    "timestamp_image_url",
    "image_status",  # [pending, approved, denied]
    "step_state",  # [epic_name, image_proof, video_proof] - Tracks user progress
    "points_assigned"
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
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(user_data, file, indent=4)

# ✅ Load user data
def load_user_data(discord_id):
    """Loads a user's data from their JSON file."""
    file_path = get_user_file(discord_id)

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    return None  # User file does not exist

# ✅ Get User Entry
def get_user_entry(discord_id):
    """Retrieves a user's data from their JSON file."""
    return load_user_data(discord_id)  # Returns None if user doesn't exist

# END OF GET



# POST

# ✅ Save user data
def save_user_data(discord_id, data):
    """Saves user data to their individual JSON file."""
    file_path = get_user_file(discord_id)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

# ✅ Save Epic Games ID
def save_epic_name_to_database(discord_id, epic_name):
    """Saves the Epic Games ID for a user."""
    initialize_key(discord_id)  # Ensure user file exists
    user_data = load_user_data(discord_id)  # Load current data

    user_data["epic_name"] = epic_name
    user_data["timestamp_epic_name"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    save_user_data(discord_id, user_data)  # Save back to file
    print(f"✅ Saved Epic Games ID for user {discord_id}")

# ✅ Save Image Proof
def save_image_to_database(discord_id, image_url):
    """Saves the image URL for a user."""
    initialize_key(discord_id)  # Ensure user file exists
    user_data = load_user_data(discord_id)  # Load current data

    user_data["image_url"] = image_url
    user_data["timestamp_image_url"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    save_user_data(discord_id, user_data)  # Save back to file
    print(f"✅ Saved image proof for user {discord_id}")

# --- END OF POST ---



# --- CLI Commands for Testing ---
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "populate":
        for i in range(1, 100000):
            save_epic_name_to_database(i, f"epic_name_{i}")

    elif len(sys.argv) > 1 and sys.argv[1] == "getkey":
        print(get_user_entry("99998"))

    elif len(sys.argv) > 1 and sys.argv[1] == "DELETE":
        for filename in os.listdir(DB_DIR):
            file_path = os.path.join(DB_DIR, filename)
            os.remove(file_path)

        print("✅ Delete complete!")
    else:
        print("No argument provided!")
