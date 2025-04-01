import os
import sys
import discord
from discord.ext import commands
from discord.ui import View, Button
from config import TOKEN_play2earn
from play2earn_bot import SupportView

if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.members = True
    play2earn_bot = commands.Bot(command_prefix="!", intents=intents)

    







    @play2earn_bot.event
    async def on_ready():
        print("ready BEGIN")
        def get_role(role_name):
            return discord.utils.get(guild.roles, name=role_name)
    
        print(f"✅ Logged in as {play2earn_bot.user}")
    
        guild = play2earn_bot.get_guild(GUILD_ID)
    
        welcome_channel = play2earn_bot.get_channel(WELCOME_CHANNEL_ID)
        rules_channel = play2earn_bot.get_channel(RULES_CHANNEL_ID)
        support_channel = play2earn_bot.get_channel(SUPPORT_CHANNEL_ID)
        creator_channel = play2earn_bot.get_channel(CREATORS_CHANNEL_ID)
        print(welcome_channel, rules_channel, support_channel)
        if not welcome_channel or not rules_channel or not support_channel:
            print("❌ Channel not found.")
            return

        # --- WELCOME MESSAGE ---
        
        giveaway_embed = discord.Embed(
            title="",
            description="### Welcome to the Official Discord Server of the Play2Earn 1v1 Map!",
            color=discord.Color.from_rgb(0, 255, 255)  # Cyan
        )
        giveaway_embed.add_field(name="\n", value="", inline=False)

        giveaway_embed.add_field(
            name="🌍 Our Mission",
            value=(
                "The Fortnite Island Creator Program gives 40% of Fortnite’s revenue to map creators — "
                "but most of that money goes to a few big creators.\n"
                "**We're here to change that!**\n"
                "Play2Earn is a **community-driven project** built to share that income fairly with the entire Fortnite community. "
                "Instead of making a few creators rich, **we want everyone to get a piece of the cake!**\n"
                "Play2Earn isn’t just another random 1v1 Map — it’s a **movement to reshape Fortnite’s creator economy**.\n"
                "We're building a fairer system where **everyone** can benefit — not just the top few."
            ),
            inline=False
        )
        giveaway_embed.add_field(name="\n", value="", inline=False)
        giveaway_embed.add_field(
            name="🚀 How to Join the Giveaway",
            value=(
                "**1.** Play the map **Play2Earn 1v1**\n"
                "**2.** Press the **UPLOAD** button in the map and take a screenshot of it\n"
                "**3.** Head to `#submit-proof`, click **Verify** and go to your DMs\n"
                "**4.** Link your Epic account and send your screenshot to the **SupportYourCreator Bot**\n"
                "**5.** Once approved, you'll get access to the `🔒 🎁giveaway🎁` channel\n"
                "**6.** React to the ✋ emoji to officially enter the giveaway 🎉"
            ),
            inline=False
        )
        giveaway_embed.add_field(name="\n", value="", inline=False)
        giveaway_embed.add_field(
            name="📈 How Your Chances Are Calculated",
            value=(
                "- **1 hour played = +1x chance** to win\n"
                "- **1 successful invite = +1x chance** to win\n"
                "- More average players = more income = bigger prize pool 💰\n"
                "There’s no limit — the more you play and share, the better your odds!"
            ),
            inline=False
        )
        giveaway_embed.add_field(name="\n", value="", inline=False)
        giveaway_embed.add_field(
            name="💸 Where Does the Money Go?",
            value=(
                "All of this comes from the **map’s income**.\n"
                "- **60%** is given back to the community through giveaways\n"
                "- **35%** goes to **content creators** via invite rewards\n"
                "- **5%** supports project development and maintenance"
            ),
            inline=False
        )
        giveaway_embed.add_field(name="\n", value="", inline=False)
        current_pool_channel = play2earn_bot.get_channel(1354449930323886266)
        giveaway_embed.add_field(
            name="📅🎁 When’s the Next Giveaway?",
            value=(
                f"The next giveaway will be on Sunday 13th April 2025. {current_pool_channel.mention}\n"
                "Based on current trends, **1 hour of playtime = approx. $0.05** *(estimate only)*."
            ),
            inline=False
        )
        giveaway_embed.add_field(name="\n", value="", inline=False)
        giveaway_embed.add_field(name="\n", value="", inline=False)
        giveaway_embed.add_field(name="\n", value="", inline=False)
        giveaway_embed.add_field(
            name="🏆 Player Roles",
            value=(
                f"{get_role('Verified').mention} → Linked Epic Games account\n\n"
                f"{get_role('Bronze').mention} → Played **0 minutes** (newly joined)\n"
                f"{get_role('Gold').mention} → Played **120 minutes**\n"
                f"{get_role('Diamond').mention} → Played **500 minutes**\n"
                f"{get_role('Champion').mention} → Played **1,200 minutes**\n"
                f"{get_role('Unreal').mention} → Played **6,000 minutes**"
            ),
            inline=False
        )


        # --- END OF WELCOME MESSAGE ---

        

        # --- RULES MESSAGE ---

        rules_embed = discord.Embed(
            title="📜 Server Rules",
            color=discord.Color.red()
        )
        rules_embed.add_field(
            name="1) General",
            value="• Chat in English, be respectful. Spam, advertisement, hate-speech, racism, sexual harassment, threats, impersonation will result in a ban!",
            inline=False
        )
        rules_embed.add_field(
            name="2) Disputes",
            value="• Do not start or bring any unnecessary drama. Topics such as religion and politics are deemed too inflammatory/controversial and provocative. Issues with other members may only be solved in private.",
            inline=False
        )
        rules_embed.add_field(
            name="3) Privacy",
            value="• You may neither publicly nor privately expose any personal information of any member in this server.",
            inline=False
        )
        rules_embed.add_field(
            name="4) Terms of Service",
            value="• Please follow the Discord & Epic Games Terms of Service. Failing to do so will result in a ban.",
            inline=False
        )
        rules_embed.add_field(
            name="5) Cheating",
            value="• Gaining an unfair advantage over others is strictly prohibited. For example, do not share your playtime proof with others or attempt to bypass the verification system. Doing so will result in a ban. All giveaway winners will be manually verified after the draw – cheating will not be successful.",
            inline=False
        )
        # --- END OF RULES MESSAGE ---

        
        
        # --- SUPPORT MESSAGE ---

        support_embed = discord.Embed(
            title="Play2Earn Ticketsystem",
            description="Here you can contact support for any concerns.\n"
                        "For public questions you can also use the `#ask-a-mod` channel.",
            color=discord.Color.green()
        )

        

        support_view = SupportView()


        # --- END OF SUPPORT MESSAGE ---


        
        # --- CREATORS MESSAGE ---

        creator_embed = discord.Embed(
            title="",
            description="### 🤝 Content Creator Partnership – Earn with the Play2Earn 1v1 Map",
            color=discord.Color.gold()
        )
        creator_embed.add_field(name="\n", value="", inline=False)
        creator_embed.add_field(
            name="💰 Earn by Sharing",
            value=(
                "You're invited to become a **partnered content creator** with Play2Earn!\n\n"
                "- **35%** of all income from players who join via your Discord invite **goes to you**\n"
                "- **5%** supports the project\n"
                "- **60%** is reinvested into **community giveaways**\n"
                "*Estimated: 1 hour of playtime = approx. **$0.05** (subject to change)*\n"
            ),
            inline=False
        )
        creator_embed.add_field(name="\n", value="", inline=False)
        creator_embed.add_field(
            name="✅ How to Get Started",
            value=(
                "**1.** Open a **support ticket** in the `#support` channel and let us know that you're interested in joining the Content Creator Program\n"
                "**2.** Create a **permanent invite link** to the Play2Earn 1v1 Discord Server\n"
                "**3.** **Share your invite link and promote the map to your community**\n"
                "**4.** **Track your referrals** using the `!creator` command in the same support ticket\n"
                "**5.** **Request payout** anytime in the same support ticket"
            ),
            inline=False
        )
        creator_embed.add_field(name="\n", value="", inline=False)
        creator_embed.add_field(
            name="🌟 Why This Matters",
            value=(
                "Play2Earn isn’t just another random 1v1 Map — it’s a **movement to reshape Fortnite’s creator economy**.\n"
                "We're building a fairer system where **everyone** can benefit — not just the top few.\n\n"
                "Join us in leading this shift!"
            ),
            inline=False
        )

        # --- END OF CREATORS MESSAGE ---


        
    
        if sys.argv[1] == "XXXsendXXX": # sends annoying notification to all users
            #await welcome_channel.send(embed=giveaway_embed)
            #await rules_channel.send(embed=rules_embed)
            #await support_channel.send(embed=support_embed, view=support_view)
            #await creator_channel.send(embed=creator_embed)
            pass
        elif sys.argv[1] == "edit":
            welcome_message = await welcome_channel.fetch_message(WELCOME_MESSAGE_ID)
            await welcome_message.edit(embed=giveaway_embed)
            
            rules_message = await rules_channel.fetch_message(RULES_MESSAGE_ID)
            await rules_message.edit(embed=rules_embed)
            
            support_message = await support_channel.fetch_message(SUPPORT_MESSAGE_ID)
            await support_message.edit(embed=support_embed, view=support_view)

            creator_message = await creator_channel.fetch_message(CREATORS_MESSAGE_ID)
            await creator_message.edit(embed=creator_embed)
            print("✅ Messages edited successfully!")
    
        print("✅ Messages sent!")
        await play2earn_bot.close()



    
    

    ENVIRONMENT = "production" #"development"

    if ENVIRONMENT == "production":
        GUILD_ID = 1350609155525967892 # Play2Earn 1v1 Discord Server
        
        WELCOME_CHANNEL_ID = 1351627040893173953
        WELCOME_MESSAGE_ID = 1353436242074664992 # change if necessary

        RULES_CHANNEL_ID = 1352810310251188255
        RULES_MESSAGE_ID = 1353436243374903439

        SUPPORT_CHANNEL_ID = 1351340480239112305
        SUPPORT_MESSAGE_ID = 1353436244339851316

        CREATORS_CHANNEL_ID = 1354815281528176862
        CREATORS_MESSAGE_ID = 1354820458461266203
        
        play2earn_bot.run(os.getenv("DISCORD_TOKEN_PLAY2EARN_PROD"))
    elif ENVIRONMENT == "development":
        GUILD_ID = 1329571928482250834 # SYC Dev Discord Server
        WELCOME_CHANNEL_ID = 1338874327650533397
        WELCOME_MESSAGE_ID = 1353425136644263989  # change if necessary

        RULES_CHANNEL_ID = 1338874457598460035
        RULES_MESSAGE_ID = 1353425137344712827

        SUPPORT_CHANNEL_ID = 1353413783732748420
        SUPPORT_MESSAGE_ID = 1353434582271135874

        CREATORS_CHANNEL_ID = 000
        CREATORS_MESSAG_ID = 000
        
        play2earn_bot.run(TOKEN_play2earn)




