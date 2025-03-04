import json
import asyncpg
import asyncio
import os
import shutil
import sys
import requests
import logging
import aiohttp
import aiofiles
from datetime import datetime
from replit.object_storage import Client
from config import OBJECT_STORAGE_BUCKET_ID, DATABASE_URL, LOGGING_LEVEL
from queues import PGQueue, ObjectStorageQueue


# ✅ Setup logging configuration
logging.basicConfig(
    level=LOGGING_LEVEL,  # Capture ALL logs (INFO, DEBUG, ERROR)  # Set to DEBUG if you want to see debug logs of discord.http's request function
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # Ensure logs are printed to Replit console
    ]
)
logger = logging.getLogger(__name__)  # ✅ Use logger instead of print()


logger.info(f"📁 Database URL: {DATABASE_URL}")

db_pool = None
logger.info("✅✅✅✅✅   db_pool = None  ✅✅✅✅✅")
bucketClient = Client(bucket_id=OBJECT_STORAGE_BUCKET_ID)

pg_queue = PGQueue(max_workers=4) 
object_storage_queue = ObjectStorageQueue(max_workers=4) # increase max_workers to parallelize uploads
logger.info("✅ Created PGQueue and ObjectStorageQueue successfully!")

PG_SEMAPHORE = asyncio.Semaphore(10)  # Limit the number of concurrent database operations to 10
OBJECT_STORAGE_SEMAPHORE = asyncio.Semaphore(10) # to prevent "Connection pool is full, discarding connection: storage.googleapis.com. Connection pool size: 10"

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
    "step_state",  # [epic_name, wait, image_proof] - Tracks user progress.
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

async def download_image(media_url, image_name):
    """Downloads an image asynchronously and saves it locally."""
    try:
        file_path = os.path.join(DB_DIR, image_name)

        async with aiohttp.ClientSession() as session:
            async with session.get(media_url) as response:
                response.raise_for_status()

                async with aiofiles.open(file_path, "wb") as image_file:
                    await image_file.write(await response.read())

        # ✅ Queue upload instead of blocking
        asyncio.create_task(object_storage_queue.add_task(async_upload_to_object_storage, file_path, image_name))

        logger.info(f"✅ Image {image_name} saved locally and queued for object storage upload.")
        return file_path
    except Exception as e:
        logger.info(f"❌ Failed to download image: {e}")
        return None




async def async_upload_to_object_storage(file_path, medium_name):
    """Asynchronously uploads a file to Replit Object Storage."""
    async with OBJECT_STORAGE_SEMAPHORE:
        try:
            await asyncio.to_thread(bucketClient.upload_from_filename, medium_name, file_path)
            logger.info(f"✅ Asynchronously uploaded {medium_name} to object storage.")
        except Exception as e:
            logger.info(f"❌ Failed to upload {medium_name} to object storage: {e}")

# END OF GET





# POST

# ✅ Save user data
def save_user_data(discord_id, data, only_local=False, loop=None):
    """Saves user data to their individual JSON file and updates PostgreSQL asynchronously."""
    file_path = get_user_file(discord_id)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

    if not only_local:
        #✅ Add database save to queue instead of direct call
        if loop:
            loop.create_task(pg_queue.add_task(save_user_data_to_pg, discord_id, data=data))
            logger.debug(f"✅ /notify save_user_data_to_pg() scheduled in bot loop for {discord_id} for ")
        else:
            try:
                running_loop = asyncio.get_running_loop()
                running_loop.create_task(pg_queue.add_task(save_user_data_to_pg, discord_id, data=data))
            except RuntimeError:
                asyncio.run(pg_queue.add_task(save_user_data_to_pg, discord_id, data=data))  # Blocking fallback

        logger.debug(f"✅ save_user_data_to_pg() queued for {discord_id}")




# ✅ Save DM link
def save_dm_link_to_database(discord_id, dm_link):
    """Saves the Epic Games ID for a user."""
    initialize_key(discord_id)  # Ensure user file exists
    user_data = load_user_data(discord_id)  # Load current data

    user_data["dm_link"] = dm_link 

    save_user_data(discord_id, user_data)  # Save back to file
    logger.info(f"✅ Saved Epic Games ID for user {discord_id}")

# ✅ Save Epic Games ID
def save_epic_name_to_database(discord_id, discord_name, epic_name):
    """Saves the Epic Games ID for a user."""
    initialize_key(discord_id)  # Ensure user file exists
    user_data = load_user_data(discord_id)  # Load current data

    if (user_data["epic_name"] is None):
        user_data["epic_name"] = str(epic_name)
        user_data["discord_name"] = str(discord_name)
        user_data["timestamp_epic_name"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        user_data["step_state"] = "image_proof"  # The user's next step is to upload image proof
        
    else: # user proofed already epic name
        logger.info(f"❌ User {discord_id} already proofed their Epic Games name {user_data['epic_name']}")
        return False

    save_user_data(discord_id, user_data)  # Save back to file
    logger.info(f"✅ Saved Epic Games ID for user {discord_id}")
    return True

# ✅ Save Image Proof
async def save_image_to_database(discord_id, image_url):
    """Saves the image data for a user."""
    initialize_key(discord_id)  # Ensure user file exists
    user_data = load_user_data(discord_id)  # Load current data

    # Download image from Discord's CDN
    image_name = f"{discord_id}_{len(user_data['images']) + 1}.png"
    downloaded_image_path = await download_image(image_url, image_name)

    # Add image data to the user's images list
    user_data["images"].append({
        "image_url_cdn": image_url,
        "image_path": downloaded_image_path,
        "timestamp_uploaded": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "image_status": "pending"
    })
    user_data["step_state"] = "wait"  # The user should wait for a response

    save_user_data(discord_id, user_data)  # Save back to file
    logger.info(f"✅ Saved image proof for user {discord_id}")


# --- END OF POST ---



# POSTGRESQL
 
async def init_pg():
    """Initializes PostgreSQL: Creates connection pool, ensures table, and restores filesystem."""
    asyncio.create_task(pg_queue.start_workers())
    asyncio.create_task(object_storage_queue.start_workers())  # Start object storage workers
    logger.info("✅ Started workers for PGQueue and ObjectStorageQueue successfully!")
    
    global db_pool
    logger.info(f"🔄 Initializing PostgreSQL with DATABSE_URL: {DATABASE_URL}")
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)  # Limit connections
        logger.info("✅ PostgreSQL initialized successfully!")
    except Exception as e:
        logger.info(f"❌ Failed to initialize PostgreSQL: {e}")
    await create_table()  # Ensure DB structure
    await restore_filesystem_from_db()  # Restore filesystem from DB
    logger.info("✅ PostgreSQL initialized successfully.")

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
                step_state TEXT,
                points_assigned INTEGER DEFAULT 0,
                reacted_hand BOOLEAN DEFAULT FALSE
            )
        """)
    logger.info("✅ Database table ensured.")

async def restore_filesystem_from_db():
    """Restores the local filesystem from PostgreSQL on bot startup, including pending images."""
    # Begrenze gleichzeitige Downloads auf 8, um den Pool von 10 nicht zu überlasten

    async def download_image_from_bucket(image_name, file_path):
        """Wrapper to download images mit Rate-Limitierung."""
        async with OBJECT_STORAGE_SEMAPHORE:  # Begrenze gleichzeitige Downloads
            try:
                await asyncio.to_thread(bucketClient.download_to_filename, image_name, file_path)
                logger.info(f"✅ Restored pending image {image_name} from object storage to {file_path}")
            except Exception as e:
                logger.error(f"❌ Failed to restore image {image_name}: {e}")


    
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM users")

        tasks = []  # Store tasks for concurrent execution

        for row in rows:
            user_data = {
                "discord_id": row["discord_id"],
                "discord_name": row["discord_name"],
                "dm_link": row["dm_link"],
                "epic_name": row["epic_name"],
                "timestamp_epic_name": row["timestamp_epic_name"],
                "images": json.loads(row["images"]),
                "step_state": row["step_state"],
                "points_assigned": row["points_assigned"],
                "reacted_hand": row["reacted_hand"]
            }

            # ✅ Save user data in the filesystem
            save_user_data(user_data["discord_id"], user_data, only_local=True)
            logger.info(f"✅ Restored user {row['discord_id']} from PostgreSQL to filesystem")

            # ✅ Restore pending images from Object Storage
            for image in user_data["images"]:
                if image["image_status"] == "pending":
                    image_name = os.path.basename(image["image_path"])
                    file_path = os.path.join(DB_DIR, image_name)

                    if not os.path.exists(file_path):
                        tasks.append(download_image_from_bucket(image_name, file_path))

        # Run all downloads concurrently
        await asyncio.gather(*tasks)

    



async def save_user_data_to_pg(discord_id, data):
    """Saves user data asynchronously in PostgreSQL."""
    logger.debug(f" db_pool check: {db_pool}")
    try:
        async with PG_SEMAPHORE:
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO users (discord_id, discord_name, dm_link, epic_name, timestamp_epic_name, images, step_state, points_assigned, reacted_hand)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (discord_id) DO UPDATE SET
                        discord_name = EXCLUDED.discord_name,
                        dm_link = EXCLUDED.dm_link,
                        epic_name = EXCLUDED.epic_name,
                        timestamp_epic_name = EXCLUDED.timestamp_epic_name,
                        images = EXCLUDED.images,
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
                    data["step_state"],
                    data.get("points_assigned", 0),
                    data["reacted_hand"]
                )
    
                logger.debug(f"save_user_data_to_pg() executed for user {discord_id}")

    except Exception as e:
        logger.info(f"❌ Error while saving data for user {discord_id}: {e}")


async def delete_users_table():
    """Deletes all data from the 'users' table in PostgreSQL."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.info("❌ DATABASE_URL not found!")
        return

    conn = await asyncpg.connect(db_url)

    try:
        await conn.execute("TRUNCATE TABLE users CASCADE;")  # Delete all data in 'users' table
        logger.info("🗑 Cleared all data in 'users' table.")
    finally:
        await conn.close()



# --- END OF POSTGRESQL ---





# --- CLI Commands for Testing ---
if __name__ == "__main__":

    if len(sys.argv) > 2 and sys.argv[1] == "populate":
        for i in range(1, int(sys.argv[2]) + 1):
            save_epic_name_to_database(i, f"discord_name_{i}", f"epic_name_{i}")

    elif len(sys.argv) > 1 and sys.argv[1] == "getkey":
        logger.info(load_user_data("99998"))

    elif len(sys.argv) > 1 and sys.argv[1] == "DELETE":
        # delete user entries in filesystem
        if os.path.exists(DB_DIR):
            shutil.rmtree(DB_DIR)
            logger.info(f"🗑️ Deleted directory: {DB_DIR}")
        else:
            logger.info(f"❌ Directory does not exist: {DB_DIR}")
        os.makedirs(DB_DIR, exist_ok=True)  # reset the database
        # delete user entries in postgresql
        asyncio.run(delete_users_table())
        # delete images in object storage bucket
        for key in bucketClient.list():
            logger.info(key.name)
            bucketClient.delete(key.name)
            logger.info(f"🗑 Deleted object: {key.name}")
        logger.info("✅ Delete complete!")

    else:
        logger.info("No argument provided!")

