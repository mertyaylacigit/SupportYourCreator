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
DISCORD_BOT_URL = "http://127.0.0.1:5001/notify"

CATEGORY_ID = 1329571928482250835
WELCOME_CHANNEL_ID = 1329571928951754823
GUILD_ID = 1329571928482250834
GIVEAWAY_CHANNEL_ID = 1338535496581644420
FAQ_CHANNEL_ID = 1338868370132435004
TESTING_CHANNEL_ID = 1339342650444091423
MERT_DISCORD_ID = 404403851505172532

IMAGESVIDEOS_BUCKET_ID = os.getenv("IMAGESVIDEOS_BUCKET_ID")
DATABASE_URL = os.getenv("DATABASE_URL")

# links
#randomImage1 = "https://cdn.discordapp.com/attachments/894683986868203551/1338922579213291560/ImageProofSampleBrowser.PNG?ex=67c09ed2&is=67bf4d52&hm=4215ee3088163e6109403a501e4a65e0882355da224c5dd6f83737043f27a1a7&"
sampleImageProofsFinalMergedURL = "https://cdn.discordapp.com/attachments/894683986868203551/1338928042902421656/Screenshot_2025-02-11_174148.png?ex=67c49869&is=67c346e9&hm=7ac5d9ec1dc2290a24d1c58455675ddca78460dfbac58f102bd2cdb2fa600ebd&"
sample_image_urls = [sampleImageProofsFinalMergedURL]

sample_video_urls = ["https://streamable.com/zl2w7w",
                     "https://streamable.com/24do7i"]

