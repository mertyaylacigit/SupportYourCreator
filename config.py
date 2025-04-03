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

ENVIRONMENT = os.getenv("ENVIRONMENT")
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_TIMETRACKER_KEY =  os.getenv("SECRET_TIMETRACKER_KEY")


# links
creativeMapPlayerTimeURL = "https://cdn.discordapp.com/attachments/894683986868203551/1351628595386253373/image.png?ex=67db11b9&is=67d9c039&hm=1c1ac8abb24c82cc25d109d1a7cc4f34947f2ef5fb29e7fd813a2933bddb0abb&"
sample_image_urls = [creativeMapPlayerTimeURL]

# IDs to allow slash commands
ADMIN_IDs = [404403851505172532]



if ENVIRONMENT == "production": # production/deployment
    TOKEN = os.getenv("DISCORD_TOKEN_PROD")
    TOKEN_play2earn = os.getenv("DISCORD_TOKEN_PLAY2EARN_PROD")
    EPIC_CLIENT_ID = os.getenv("EPIC_CLIENT_ID_PROD")
    EPIC_CLIENT_SECRET = os.getenv("EPIC_CLIENT_SECRET_PROD")
    EPIC_REDIRECT_URI = "https://api.supportyourcreator.com/epic_auth"  # uses supportyourcreator.com
    GUILD_ID = 1350609155525967892
    MEMBERS_STATS_ID = 1354449362880692456
    MINUTES_PLAYED_ID = 000
    PRICE_POOL_ID = 000
    SUBMIT_PROOF_CHANNEL_ID = 1351627040893173953  # Play2Earn1v1 Discord Server
    GIVEAWAY_CHANNEL_ID = 1351236909770211359  # Play2Earn1v1 Discord Server
    INVITE_CHANNEL_ID = 1352803802972946453
    OBJECT_STORAGE_BUCKET_ID = os.getenv("OBJECT_STORAGE_BUCKET_ID_PROD") # Play2Earn1v1 Bucket
    DB_TABLE = "play2earn1v1"
    ContentCreator_name = "Play2Earn1v1"
    
    send_inital_messages=False
    logger.info("Production mode enabled.")                 
else:  # development
    TOKEN = os.getenv("DISCORD_TOKEN_DEV")
    TOKEN_play2earn = os.getenv("DISCORD_TOKEN_PLAY2EARN_DEV")
    EPIC_CLIENT_ID = os.getenv("EPIC_CLIENT_ID_DEV")
    EPIC_CLIENT_SECRET = os.getenv("EPIC_CLIENT_SECRET_DEV")
    EPIC_REDIRECT_URI = "https://87b40d87-33ca-444e-a6d5-bb2e17537b90-00-26bel8cynbx4k.janeway.replit.dev/epic_auth"  # Dev redirect
    GUILD_ID = 1329571928482250834
    MEMBERS_STATS_ID = 1354233247890149527
    MINUTES_PLAYED_ID = 1354233969343860766
    PRICE_POOL_ID = 1354237265055842426
    SUBMIT_PROOF_CHANNEL_ID = 1329571928951754823 # SYC Dev Discord Server
    GIVEAWAY_CHANNEL_ID = 1338535496581644420 # SYC Dev Discord Server
    INVITE_CHANNEL_ID = 1338874480402890752
    OBJECT_STORAGE_BUCKET_ID = os.getenv("OBJECT_STORAGE_BUCKET_ID_DEV") # Dev Bucket
    DB_TABLE = "dev_db"
    ContentCreator_name = "play2earn1v1 (dev)"
    
    send_inital_messages=False
    logger.info("Development mode enabled.")
    

EPIC_OAUTH_URL = f"https://www.epicgames.com/id/authorize?client_id={EPIC_CLIENT_ID}&response_type=code&scope=basic_profile&redirect_uri={EPIC_REDIRECT_URI}"







