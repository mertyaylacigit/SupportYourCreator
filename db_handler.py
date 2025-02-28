import json
import asyncpg
import asyncio
import os
import shutil
import sys
import requests
from datetime import datetime
from replit.object_storage import Client
from config import IMAGESVIDEOS_BUCKET_ID

db_pool = None
bucketClient = Client(bucket_id=IMAGESVIDEOS_BUCKET_ID)

# Define storage location for user files
DB_DIR = "data"
os.makedirs(DB_DIR, exist_ok=True)  # Ensure directory exists

# List of attributes each user entry should have
attributes_list = [
    "discord_id",
    "discord_name",
    "dm_link",
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

def download_image(media_url, image_name):
    """Downloads a image file from the given URL in Discords CDN and saves it locally and in persistent object storage."""
    try:
        response = requests.get(media_url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Save the media file
        file_path = os.path.join(DB_DIR, image_name)
        with open(file_path, "wb") as media_file:
            media_file.write(response.content)

        # Upload the media file to persistent object storage
        # 🔄 Run upload in the background asynchronously
        asyncio.create_task(async_upload_to_object_storage(file_path, image_name))
    
        print(f"✅ Image {image_name} saved in filesystem and object storage")
        return file_path
    except requests.RequestException as e:
        print(f"❌ Failed to download image: {e}")
        return None


def download_video(streamable_url, video_name):
    """Downloads a video from Streamable and saves it locally and in persistent object storage."""
    
    def get_streamable_direct_url(streamable_url):
        """Fetches the direct MP4 URL from a Streamable video link."""
        try:
            video_id = streamable_url.split("/")[-1]  # Extract video ID from URL
            api_url = f"https://api.streamable.com/videos/{video_id}"

            response = requests.get(api_url)
            response.raise_for_status()

            data = response.json()
            if "files" in data and "mp4" in data["files"]:
                direct_url = data["files"]["mp4"]["url"]
                return direct_url
            else:
                print("❌ No direct MP4 URL found.")
                return None
        except requests.RequestException as e:
            print(f"❌ Failed to fetch Streamable metadata: {e}")
            return None

    
    try:
        direct_url = get_streamable_direct_url(streamable_url)
        if not direct_url:
            return None  # Exit if no valid direct URL

        response = requests.get(direct_url, stream=True)
        response.raise_for_status()

        # Save the video file locally
        file_path = os.path.join(DB_DIR, video_name)
        with open(file_path, "wb") as video_file:
            for chunk in response.iter_content(chunk_size=8192):
                video_file.write(chunk)

        # Upload the video file to Replit Object Storage
        # 🔄 Run upload in the background asynchronously
        asyncio.create_task(async_upload_to_object_storage(file_path, video_name))

        print(f"✅ Video {video_name} saved in filesystem and object storage")
        return file_path
    except requests.RequestException as e:
        print(f"❌ Failed to download video: {e}")
        return None

async def async_upload_to_object_storage(file_path, medium_name):
    """Asynchronously uploads a file to Replit Object Storage."""
    try:
        await asyncio.to_thread(bucketClient.upload_from_filename, medium_name, file_path)
        print(f"✅ Asynchronously uploaded {medium_name} to object storage.")
    except Exception as e:
        print(f"❌ Failed to upload {medium_name} to object storage: {e}")

# END OF GET





# POST

# ✅ Save user data
def save_user_data(discord_id, data, loop=None):
    """Saves user data to their individual JSON file and updates PostgreSQL asynchronously."""
    file_path = get_user_file(discord_id)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

    # Ensure database saving happens inside the correct event loop
    try:
        running_loop = asyncio.get_running_loop()
        running_loop.create_task(save_user_data_to_pg(discord_id, data))  # ✅ Run async if loop is active
        print(f"✅ save_user_data_to_pg() running inside existing loop for {discord_id}")
    except RuntimeError:
        if loop:
            future = asyncio.run_coroutine_threadsafe(save_user_data_to_pg(discord_id, data), loop)
            future.result()  # Ensures proper exception handling
            print(f"✅ save_user_data_to_pg() executed inside bot loop for {discord_id}")
        else:
            asyncio.run(save_user_data_to_pg(discord_id, data))  # Fallback (not recommended in prod)
            print(f"⚠️ save_user_data_to_pg() executed with asyncio.run() for {discord_id}")

        


# ✅ Save DM link
def save_dm_link_to_database(discord_id, dm_link):
    """Saves the Epic Games ID for a user."""
    initialize_key(discord_id)  # Ensure user file exists
    user_data = load_user_data(discord_id)  # Load current data

    user_data["dm_link"] = dm_link 

    save_user_data(discord_id, user_data)  # Save back to file
    print(f"✅ Saved Epic Games ID for user {discord_id}")

# ✅ Save Epic Games ID
def save_epic_name_to_database(discord_id, discord_name, epic_name):
    """Saves the Epic Games ID for a user."""
    initialize_key(discord_id)  # Ensure user file exists
    user_data = load_user_data(discord_id)  # Load current data

    save_user_data(discord_id, user_data)  # Save back to file
    print(f"✅ Saved Epic Games ID for user {discord_id}")

    if (user_data["epic_name"] is None):
        user_data["epic_name"] = str(epic_name)
        user_data["discord_name"] = str(discord_name)
        user_data["timestamp_epic_name"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        user_data["step_state"] = "image_proof"  # The user's next step is to upload image proof
        
    else: # user proofed already epic name
        print(f"❌ User {discord_id} already proofed their Epic Games name {user_data['epic_name']}")
        return False

    save_user_data(discord_id, user_data)  # Save back to file
    print(f"✅ Saved Epic Games ID for user {discord_id}")
    return True

# ✅ Save Image Proof
def save_image_to_database(discord_id, image_url):
    """Saves the image data for a user."""
    initialize_key(discord_id)  # Ensure user file exists
    user_data = load_user_data(discord_id)  # Load current data

    # Download image from Discord's CDN
    image_name = f"{discord_id}_{len(user_data['images']) + 1}.png"
    downloaded_image_path = download_image(image_url, image_name)

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

    # Download video from Streamable's CDN
    video_name = f"{discord_id}_{len(user_data['videos']) + 1}.mp4"
    downloaded_video_path = download_video(streamable_video_url, video_name)

    # Add video data to the user's videos list
    user_data["videos"].append({
        "streamable_video_url": streamable_video_url, # This url redirects to streamble.com and there I can watch/download the video
        "video_path": downloaded_video_path,
        "timestamp_uploaded": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "video_status": "pending"
    })
    user_data["step_state"] = "wait"  # The user should wait for a response

    save_user_data(discord_id, user_data)  # Save back to file
    print(f"✅ Saved video proof for user {discord_id}")

    # TODO: Find a solution to save the actual video file to the database

# --- END OF POST ---



# POSTGRESQL
 
async def init_pg():
    """Initializes PostgreSQL: Creates connection pool, ensures table, and restores filesystem."""
    global db_pool
    db_pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))  # Initialize database pool
    await create_table()  # Ensure DB structure
    await restore_filesystem_from_db()  # Restore filesystem from DB
    print("✅ PostgreSQL initialized successfully.")

async def create_table():
    """Ensures that the users table exists."""
    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                discord_id TEXT PRIMARY KEY,
                discord_name TEXT,
                dm_link TEXT,
                epic_name TEXT,
                timestamp_epic_name TEXT,
                images JSONB,
                videos JSONB,
                step_state TEXT,
                points_assigned INTEGER DEFAULT 0,
                reacted_hand BOOLEAN DEFAULT FALSE
            )
        """)
    print("✅ Database table ensured.")

async def restore_filesystem_from_db():
    """Restores the local filesystem from PostgreSQL on bot startup, including pending images."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM users")

        for row in rows:
            user_data = {
                "discord_id": row["discord_id"],
                "discord_name": row["discord_name"],
                "dm_link": row["dm_link"],
                "epic_name": row["epic_name"],
                "timestamp_epic_name": row["timestamp_epic_name"],
                "images": json.loads(row["images"]),
                "videos": json.loads(row["videos"]),
                "step_state": row["step_state"],
                "points_assigned": row["points_assigned"],
                "reacted_hand": row["reacted_hand"]
            }

            # ✅ Save user data in the filesystem
            save_user_data(user_data["discord_id"], user_data)
            print(f"✅ Restored user {row['discord_id']} from PostgreSQL to filesystem")

            # ✅ Restore pending images from Object Storage
            for image in user_data["images"]:
                if image["image_status"] == "pending":  # Only restore pending images
                    image_name = os.path.basename(image["image_path"])
                    file_path = os.path.join(DB_DIR, image_name)

                    # Check if file already exists locally
                    if not os.path.exists(file_path):
                        try:
                            # Save image from Replit Object Storage to fileystem database
                            bucketClient.download_to_filename(image_name, file_path)

                            print(f"✅ Restored pending image {image_name} from object storage to {file_path}")

                        except Exception as e:
                            print(f"❌ Failed to restore image {image_name}: {e}")

            # ✅ Restore pending videos from Object Storage
            for video in user_data["videos"]:
                if video["video_status"] == "pending":  # Only restore pending video
                    video_name = os.path.basename(video["video_path"])
                    file_path = os.path.join(DB_DIR, video_name)

                    # Check if file already exists locally
                    if not os.path.exists(file_path):
                        try:
                            # Save video from Replit Object Storage to fileystem database
                            bucketClient.download_to_filename(video_name, file_path)

                            print(f"✅ Restored pending video {video_name} from object storage to {file_path}")

                        except Exception as e:
                            print(f"❌ Failed to restore video {video_name}: {e}")



async def save_user_data_to_pg(discord_id, data):
    """Saves user data asynchronously in PostgreSQL."""
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (discord_id, discord_name, dm_link, epic_name, timestamp_epic_name, images, videos, step_state, points_assigned, reacted_hand)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (discord_id) DO UPDATE SET
                    discord_name = EXCLUDED.discord_name,
                    dm_link = EXCLUDED.dm_link,
                    epic_name = EXCLUDED.epic_name,
                    timestamp_epic_name = EXCLUDED.timestamp_epic_name,
                    images = EXCLUDED.images,
                    videos = EXCLUDED.videos,
                    step_state = EXCLUDED.step_state,
                    points_assigned = EXCLUDED.points_assigned,
                    reacted_hand = EXCLUDED.reacted_hand
            """, 
                str(discord_id),
                data["discord_name"],
                data["dm_link"],
                data["epic_name"],
                data["timestamp_epic_name"],
                json.dumps(data["images"]),
                json.dumps(data["videos"]),
                data["step_state"],
                data.get("points_assigned", 0),
                data["reacted_hand"]
            )

            print(f"✅ Data insert executed for user {discord_id}")

    except Exception as e:
        print(f"❌ Error while saving data for user {discord_id}: {e}")


async def delete_users_table():
    """Deletes all data from the 'users' table in PostgreSQL."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not found!")
        return

    conn = await asyncpg.connect(db_url)

    try:
        await conn.execute("TRUNCATE TABLE users CASCADE;")  # Delete all data in 'users' table
        print("🗑 Cleared all data in 'users' table.")
    finally:
        await conn.close()



# --- END OF POSTGRESQL ---





# --- CLI Commands for Testing ---
if __name__ == "__main__":

    if len(sys.argv) > 2 and sys.argv[1] == "populate":
        from config import sample_image_urls, sample_video_urls
        for i in range(1, int(sys.argv[2]) + 1):
            save_epic_name_to_database(i, f"discord_name_{i}", f"epic_name_{i}")

    elif len(sys.argv) > 1 and sys.argv[1] == "getkey":
        print(load_user_data("99998"))

    elif len(sys.argv) > 1 and sys.argv[1] == "DELETE":
        # delete user entries in filesystem
        if os.path.exists(DB_DIR):
            shutil.rmtree(DB_DIR)
            print(f"🗑️ Deleted directory: {DB_DIR}")
        else:
            print(f"❌ Directory does not exist: {DB_DIR}")
        os.makedirs(DB_DIR, exist_ok=True)  # reset the database
        # delete user entries in postgresql
        asyncio.run(delete_users_table())
        # delete images/videos in object storage bucket
        for key in bucketClient.list():
            print(key.name)
            bucketClient.delete(key.name)
            print(f"🗑 Deleted object: {key.name}")
        print("✅ Delete complete!")

    else:
        print("No argument provided!")

