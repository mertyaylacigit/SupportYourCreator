import os

TOKEN = os.getenv("TOKEN")
EPIC_CLIENT_ID = os.getenv("EPIC_CLIENT_ID")
EPIC_CLIENT_SECRET = os.getenv("EPIC_CLIENT_SECRET")
EPIC_REDIRECT_URI = "https://87b40d87-33ca-444e-a6d5-bb2e17537b90-00-26bel8cynbx4k.janeway.replit.dev/epic_auth"
EPIC_OAUTH_URL = f"https://www.epicgames.com/id/authorize?client_id={EPIC_CLIENT_ID}&response_type=code&scope=basic_profile&redirect_uri={EPIC_REDIRECT_URI}"
CATEGORY_ID = 1329571928482250835
WELCOME_CHANNEL_ID = 1329571928951754823
GUILD_ID = 1329571928482250834
GIVEAWAY_CHANNEL_ID = 1338535496581644420
FAQ_CHANNEL_ID = 1338868370132435004
TESTING_CHANNEL_ID = 1339342650444091423
MERT_DISCORD_ID = 404403851505172532

# links
randomImage1 = "https://cdn.discordapp.com/attachments/894683986868203551/1338922171946500197/imageProofSampleInGame.PNG?ex=67ae2971&is=67acd7f1&hm=0c88093382778db49632c33114970df429610844c3ce79ec3f8c824a46bb7c86&"
sampleImageProofsFinalMergedURL = "https://cdn.discordapp.com/attachments/894683986868203551/1338928042902421656/Screenshot_2025-02-11_174148.png?ex=67ae2ee9&is=67acdd69&hm=40d57688be7a126f677a0bc6c4364d63bea98060e4e25dd00b53c8ca3325b716&"
sample_image_urls = [sampleImageProofsFinalMergedURL, randomImage1]

sample_video_urls = ["https://streamable.com/zl2w7w",
                     "https://streamable.com/cnsugr"]

