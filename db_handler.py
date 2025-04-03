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
from config import OBJECT_STORAGE_BUCKET_ID, DATABASE_URL, LOGGING_LEVEL, DB_TABLE
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

pg_queue = PGQueue(max_workers=1) 
object_storage_queue = ObjectStorageQueue(max_workers=1) # increase max_workers to parallelize uploads
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
    "images",  # List of images
    "step_state",  # [image_proof] - Tracks user progress. Always image proof. I removed video and epic verification
    "points_assigned",
    "invite"
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
        user_data["step_state"] = "image_proof"  # The user's next step is to submit proof
        user_data["invite"] = {"used_code": None, "inviter_id": None, "invited_users": [], "total_invites": 0}
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
def save_dm_link_to_database(discord_id, discord_name, dm_link):
    """Saves the dm link for a user."""
    initialize_key(discord_id)  # Ensure user file exists
    user_data = load_user_data(discord_id)  # Load current data

    user_data["discord_name"] = str(discord_name)
    user_data["dm_link"] = dm_link 

    save_user_data(discord_id, user_data)  # Save back to file
    logger.info(f"✅ Saved dml link for user {discord_id}")


# ✅ Save Image Proof
async def save_image_proof_decision(discord_id, image_url, decision):
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
        "image_status": "approved" if "valid_hash" in decision and decision["valid_hash"] else "denied",
        "played_time": decision.get("played_time", 0),
        "error" : decision["error"] if "error" in decision else ""
    })

    if "error" in decision:
        pass
    elif "valid_hash" in decision and "played_time" in decision:
        # ✅ Update user progress state
        if decision["valid_hash"]:
            user_data["points_assigned"] = decision["played_time"]  # Grant points based on playtime
        
        user_data["step_state"] = "image_proof"
    
    save_user_data(discord_id, user_data)  # Save back to file
    logger.info(f"✅ Saved image proof for user {discord_id}")


def save_invite_join_to_database(member, used_invite):
    inviter = used_invite.inviter
    initialize_key(inviter.id)
    inviter_data = load_user_data(inviter.id)

    inviter_data["invite"]["invited_users"].append(str(member.id))
    inviter_data["invite"]["total_invites"] += 1
    save_user_data(inviter.id, inviter_data)

    # new member joined to discord server
    initialize_key(member.id)
    new_user_data = load_user_data(member.id)
    
    new_user_data["invite"]["used_code"] = used_invite.code
    new_user_data["invite"]["inviter_id"] = str(inviter.id)
    save_user_data(member.id, new_user_data)

    return inviter_data["invite"]["total_invites"]



def save_invite_remove_to_database(left_member, inviter_id):
    initialize_key(left_member.id)
    left_member_data = load_user_data(left_member.id)

    left_member_data["invite"]["used_code"] = None
    left_member_data["invite"]["inviter_id"] = None
    save_user_data(left_member.id, left_member_data)
    
    inviter_data = load_user_data(inviter_id)
    if inviter_data:
        invited_users = inviter_data["invite"].get("invited_users", [])
        if str(left_member.id) in invited_users:
            invited_users.remove(str(left_member.id))
            inviter_data["invite"]["total_invites"] -= 1
            save_user_data(inviter_id, inviter_data)
            
        return inviter_data["invite"]["total_invites"]


def restore_invite_user_map():
    restored_map = {}

    for filename in os.listdir(DB_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(DB_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as file:
                user_data = json.load(file)
                discord_id = int(user_data["discord_id"])
                invite_info = user_data.get("invite", {})

                used_code = invite_info.get("used_code")
                inviter_id = invite_info.get("inviter_id")

                if used_code and inviter_id:
                    restored_map[discord_id] = (used_code, int(inviter_id))

    return restored_map
    


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
    """Ensures that the {DB_TABLE} table exists."""
    async with db_pool.acquire() as conn:
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {DB_TABLE} (
                discord_id TEXT PRIMARY KEY,
                discord_name TEXT,
                dm_link TEXT,
                images JSONB,
                step_state TEXT,
                points_assigned INTEGER DEFAULT 0,
                invite JSONB
            )
        """)
    logger.info("✅ Database table ensured.")

async def restore_filesystem_from_db():
    """Restores the local filesystem from PostgreSQL on bot startup, including pending images."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(f"SELECT * FROM {DB_TABLE}")

        for row in rows:
            user_data = {
                "discord_id": row["discord_id"],
                "discord_name": row["discord_name"],
                "dm_link": row["dm_link"],
                "images": json.loads(row["images"]),
                "step_state": row["step_state"],
                "points_assigned": row["points_assigned"],
                "invite": json.loads(row["invite"])
            }

            # ✅ Save user data in the filesystem
            save_user_data(user_data["discord_id"], user_data, only_local=True)
            logger.info(f"✅ Restored user {row['discord_id']} from PostgreSQL to filesystem")



async def restore_user_from_db(discord_id: int):
    """Fetches and restores a specific user's data from PostgreSQL to the local cache."""
    # This function is called by the discord slash command /restore_user
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT * FROM {DB_TABLE} WHERE discord_id = $1", str(discord_id))

        if not row:
            logger.warning(f"❌ No data found for user {discord_id}.")
            return None  # Return None if user is not found

        user_data = {
            "discord_id": row["discord_id"],
            "discord_name": row["discord_name"],
            "dm_link": row["dm_link"],
            "images": json.loads(row["images"]),
            "step_state": row["step_state"],
            "points_assigned": row["points_assigned"],
            "invite": json.loads(row["invite"])
        }

        # ✅ Save user data in the filesystem
        save_user_data(user_data["discord_id"], user_data, only_local=True)

        logger.info(f"✅ Restored user {row['discord_id']} from PostgreSQL to filesystem")
        return user_data  # Return data if successful



async def save_user_data_to_pg(discord_id, data):
    """Saves user data asynchronously in PostgreSQL."""
    logger.debug(f" db_pool check: {db_pool}")
    try:
        async with PG_SEMAPHORE:
            async with db_pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {DB_TABLE} (discord_id, discord_name, dm_link, images, step_state, points_assigned, invite)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (discord_id) DO UPDATE SET
                        discord_name = EXCLUDED.discord_name,
                        dm_link = EXCLUDED.dm_link,
                        images = EXCLUDED.images,
                        step_state = EXCLUDED.step_state,
                        points_assigned = EXCLUDED.points_assigned,
                        invite = EXCLUDED.invite
                """, 
                    str(discord_id),
                    data["discord_name"],
                    data["dm_link"],
                    json.dumps(data["images"]),
                    data["step_state"],
                    data.get("points_assigned", 0),
                    json.dumps(data["invite"])
                )
    
                logger.debug(f"save_user_data_to_pg() executed for user {discord_id}")

    except Exception as e:
        logger.info(f"❌ Error while saving data for user {discord_id}: {e}")


async def delete_users_table():
    """Deletes all data from the {DB_TABLE} table in PostgreSQL."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.info("❌ DATABASE_URL not found!")
        return

    conn = await asyncpg.connect(db_url)

    try:
        if DB_TABLE == "dev":
            await conn.execute(f"TRUNCATE TABLE {DB_TABLE} CASCADE;")  # Delete all data in {DB_TABLE} table
            logger.info(f"🗑 Cleared all data in {DB_TABLE} table.")
        else: 
            logger.error(f"❌ DANGER: YOU ARE TRYING TO DELETE: {DB_TABLE} table.")
    finally:
        await conn.close()



# --- END OF POSTGRESQL ---





# --- CLI Commands for Testing ---
if __name__ == "__main__":

    if len(sys.argv) > 2 and sys.argv[1] == "populate":
        for i in range(1, int(sys.argv[2]) + 1):
            pass

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

