import os
import sys
import logging
# time 23:38

LOGGING_LEVEL = logging.DEBUG # Capture ALL logs (INFO, DEBUG, ERROR)  # Set to DEBUG if you want to see debug logs of discord.http's request function

# ✅ Setup logging configuration
logging.basicConfig(
    level=LOGGING_LEVEL,  
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # Ensure logs are printed to Replit console
    ]
)
logger = logging.getLogger(__name__)  # ✅ Use logger instead of print()

TOKEN = os.getenv("TOKEN")
YUNITE_API_KEY = os.getenv("YUNITE_API_KEY")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ENVIRONMENT = os.getenv("ENVIRONMENT")

if ENVIRONMENT == "deployment": # production
    EPIC_CLIENT_ID = os.getenv("EPIC_CLIENT_ID_DEPLOYMENT")
    EPIC_CLIENT_SECRET = os.getenv("EPIC_CLIENT_SECRET_DEPLOYMENT")
    EPIC_REDIRECT_URI = "https://supportyourcreator.com/epic_auth"  # Prod redirect
    logger.info("Production mode enabled.")                 
else:  # development
    EPIC_CLIENT_ID = os.getenv("EPIC_CLIENT_ID_DEV")
    EPIC_CLIENT_SECRET = os.getenv("EPIC_CLIENT_SECRET_DEV")
    EPIC_REDIRECT_URI = "https://87b40d87-33ca-444e-a6d5-bb2e17537b90-00-26bel8cynbx4k.janeway.replit.dev/epic_auth"  # Dev redirect
    logger.info("Development mode enabled.")
    

EPIC_OAUTH_URL = f"https://www.epicgames.com/id/authorize?client_id={EPIC_CLIENT_ID}&response_type=code&scope=basic_profile&redirect_uri={EPIC_REDIRECT_URI}"

CATEGORY_ID = 1329571928482250835
WELCOME_CHANNEL_ID = 1329571928951754823
GUILD_ID = 1329571928482250834
GIVEAWAY_CHANNEL_ID = 1338535496581644420
FAQ_CHANNEL_ID = 1338868370132435004
TESTING_CHANNEL_ID = 1339342650444091423
MERT_DISCORD_ID = 404403851505172532
ContentCreator_name = "YourCreator"

IMAGESVIDEOS_BUCKET_ID = os.getenv("IMAGESVIDEOS_BUCKET_ID")
DATABASE_URL = os.getenv("DATABASE_URL")

# links
creativeMapPlayerTimeURL = "https://cdn.discordapp.com/attachments/894683986868203551/1346532831920128063/edited_image_1.png?ex=67c887ec&is=67c7366c&hm=8fdaaea3bb9bfb858b33e23444a8789bb5b98e2c292a4a1d6f3e98c6bac51073&"
sample_image_urls = [creativeMapPlayerTimeURL]

