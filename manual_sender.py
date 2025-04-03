import os
import sys
import discord
import asyncio
from multiprocessing import Process
from discord.ext import commands
from discord.ui import View, Button
from config import GIVEAWAY_CHANNEL_ID, TOKEN_play2earn
from play2earn_bot import SupportView
from main import Welcome2SubmitView

if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.members = True
    play2earn_bot = commands.Bot(command_prefix="!", intents=intents)
    bot = commands.Bot(command_prefix="!", intents=intents)

    







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
            description="### Willkommen auf dem offiziellen Discord Server der Play2Earn 1v1 Map!",
            color=discord.Color.from_rgb(0, 255, 255)  # Cyan
        )
        giveaway_embed.add_field(name="\n", value="", inline=False)

        giveaway_embed.add_field(
            name="🌍 Unsere Mission",
            value=(
                "Das Fortnite Island Creator Program gibt 40 % der Einnahmen an Map-Ersteller – "
                "aber der Großteil geht an einige wenige große Creator.\n"
                "**Wir wollen das ändern!**\n"
                "Play2Earn ist ein **Community-Projekt**, das die Einnahmen mit der ganzen Fortnite-Community teilt. "
                "Anstatt nur ein paar Creator reich zu machen, **soll auch die Community profitieren!**\n"
                "Play2Earn ist nicht einfach eine weitere random 1v1 Map – es ist eine **Bewegung, um Fortnite’s Creator-Ökonomie zu verändern**.\n"
            ),
            inline=False
        )
        giveaway_embed.add_field(name="\n", value="", inline=False)
        giveaway_embed.add_field(
            name="✅ Teilnahme am Giveaway",
            value=(
                "**1.** Spiele die **Play2Earn 1v1** Map\n"
                "**2.** Drücke den **SUBMIT**-Button in der Map und mache einen Screenshot oder ein Bild mit deinem Handy\n"
                "**3.** Klicke unten auf `Beweis senden` und gehe dann in die DMs von dem Bot\n"
                "**4.** Schicke ein Bild von Beweis deiner gespielten Minuten an den Bot\n"
                "**5.** Danach hast du Zugang auf den `🔒 🎁giveaway🎁` Kanal\n"
                "**6.** Reagiere dort auf das ✋ Emoji, um beim Giveaway teilzunehmen 🎉"
            ),
            inline=False
        )
        giveaway_embed.add_field(name="\n", value="", inline=False)
        giveaway_embed.add_field(
            name="🚀 Gewinnchancen erhöhen",
            value=(
                "- **1 Stunde gespielt = +1x Chance**\n"
                "- **1 erfolgreicher Invite = +1x Chance**\n"
                "- Mehr aktive Spieler = mehr Einnahmen = größerer Gewinn 💰"
            ),
            inline=False
        )
        giveaway_embed.add_field(name="\n", value="", inline=False)
        giveaway_embed.add_field(
            name="💸 Woher kommt das Geld?",
            value=(
                "Alles stammt aus den **Einnahmen der Map**:\n"
                "- **60 %** gehen an die Community als Giveaways\n"
                "- **35 %** an Content Creator\n"
                "- **5 %** für Projektentwicklung, Marketing & Wartung"
            ),
            inline=False
        )
        giveaway_embed.add_field(name="\n", value="", inline=False)
        current_pool_channel = play2earn_bot.get_channel(CURRENT_POOL_CHANNEL_ID)
        giveaway_embed.add_field(
            name="📅🎁 Nächstes Giveaway",
            value=(
                f"Das nächste Giveaway ist am Sonntag, den 13. April 2025. {current_pool_channel.mention}\n"
                "Aktueller Schätzwert: **1 Stunde Spielzeit = ca. $0.05** *(nur Schätzung)*."
            ),
            inline=False
        )
        giveaway_embed.add_field(name="\n", value="", inline=False)
        giveaway_embed.add_field(name="\n", value="", inline=False)
        giveaway_embed.add_field(name="\n", value="", inline=False)
        giveaway_embed.add_field(
            name="🏆 Spielerrollen",
            value=(
                f"{get_role('Bronze').mention} → **0 Minuten** gespielt (neu)\n"
                f"{get_role('Gold').mention} → **120 Minuten** gespielt\n"
                f"{get_role('Diamond').mention} → **500 Minuten** gespielt\n"
                f"{get_role('Champion').mention} → **1.200 Minuten** gespielt\n"
                f"{get_role('Unreal').mention} → **6.000 Minuten** gespielt"
            ),
            inline=False
        )


        # --- END OF WELCOME MESSAGE ---

        

        # --- RULES MESSAGE ---

        rules_embed = discord.Embed(
            title="📜 Serverregeln",
            color=discord.Color.red()
        )
        rules_embed.add_field(
            name="1) Allgemeines",
            value="• Respektvoll bleiben. Spam, Werbung, Hassrede, Rassismus, sexuelle Belästigung, Bedrohungen, Identitätsdiebstahl → Sofortiger Bann!",
            inline=False
        )
        rules_embed.add_field(
            name="2) Streitereien",
            value="• Kein unnötiges Drama. Religion und Politik sind tabu. Probleme bitte privat klären.",
            inline=False
        )
        rules_embed.add_field(
            name="3) Privatsphäre",
            value="• Keine privaten Daten anderer Mitglieder öffentlich oder privat teilen.",
            inline=False
        )
        rules_embed.add_field(
            name="4) Nutzungsbedingungen",
            value="• Bitte haltet euch an die Discord- und Epic-Games-AGBs. Verstöße → Bann.",
            inline=False
        )
        rules_embed.add_field(
            name="5) Cheating",
            value="• Kein unfairer Vorteil erlaubt (z. B. System austricksen). Alle Gewinner werden manuell geprüft.",
            inline=False
        )
        # --- END OF RULES MESSAGE ---

        
        
        # --- SUPPORT MESSAGE ---

        support_embed = discord.Embed(
            title="Play2Earn Ticketsystem",
            description="Hier kannst du den Support kontaktieren.\n"
                        "Für öffentliche Fragen nutze den `#ask-a-mod` Kanal.",
            color=discord.Color.green()
        )

        support_view = SupportView()

        # ------------------ CREATOR PROGRAMM ------------------

        creator_embed = discord.Embed(
            title="",
            description="### 🤝 Content Creator Partnerschaft – Verdiene mit der Play2Earn 1v1 Map",
            color=discord.Color.gold()
        )
        creator_embed.add_field(name="\n", value="", inline=False)
        creator_embed.add_field(
            name="💰 Verdienen durch Teilen",
            value=(
                "Werde **Partner-Content-Creator** mit Play2Earn!\n\n"
                "- **35 %** der Einnahmen von Spielern, die über deinen Invite kommen, **gehen an dich**\n"
                "- **5 %** für Projektentwicklung, Marketing & Wartung\n"
                "- **60 %** für Community-Giveaways\n"
                "*Schätzung: 1 Stunde Spielzeit = ca. **$0.05***"
            ),
            inline=False
        )
        creator_embed.add_field(name="\n", value="", inline=False)
        creator_embed.add_field(
            name="✅ So startest du",
            value=(
                "**1.** Öffne ein **Support-Ticket** im `#support` Kanal\n"
                "**2.** Erstelle einen **dauerhaften Invite-Link** zum Server\n"
                "**3.** Teile deinen Link und promote die Map\n"
                "**4.** Verfolge deine Einladungen und Earnings mit dem `!creator` Befehl\n"
                "**5.** Beantrage deine Auszahlung jederzeit im Ticket"
            ),
            inline=False
        )
        creator_embed.add_field(name="\n", value="", inline=False)
        creator_embed.add_field(
            name="🌟 Warum das wichtig ist",
            value=(
                "Play2Earn ist mehr als nur eine Map – es ist eine **Bewegung** für ein faires Fortnite-Ökosystem.\n"
                "Hilf mit, dieses System zu verändern!"
            ),
            inline=False
        )

        # --- END OF CREATORS MESSAGE ---


        
    
        if sys.argv[1] == "XXXsendXXX": # sends annoying notification to all users
            #await welcome_channel.send(embed=giveaway_embed)
            #await welcome_channel.send(embed=syc_embed, view=syc_view)
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
    
        print("✅ Messages sent by Play2Earn Bot!")
        await play2earn_bot.close()







    @bot.event
    async def on_ready():

        # --- SUPPORTYOURCREATOR MESSAGE ---


        syc_embed = discord.Embed(
            title="✅ Willkommen beim Verifizierungssystem!",
            description="Hier kannst du deine Nachweise hochladen. Klicke auf **Beweis senden**, um zu starten!",
            color=discord.Color.blue()
        )
        syc_view = Welcome2SubmitView()

        # --- END OF SUPPORTYOURCREATOR MESSAGE ---


        
        # --- GIVEAWAY MESSAGE ---

        giveaway_embed = discord.Embed(
            title="🎁 Giveaway 🎁!",
            description="\nKlicke auf ✋ um teilzunehmen!\n",
            color=discord.Color.gold()
        )
        giveaway_embed.set_footer(text="Danke für deinen Support! ❤️")       

        # --- END OF GIVEAWAY MESSAGE ---

        

        welcome_channel = bot.get_channel(WELCOME_CHANNEL_ID)
        giveaway_channel = bot.get_channel(GIVEAWAY_CHANNEL_ID)
        
        if sys.argv[1] == "XXXsendXXX": # sends annoying notification to all users
            await welcome_channel.send(embed=syc_embed, view=syc_view)
            #giveaway_message = await giveaway_channel.send(embed=giveaway_embed)
            #await giveaway_message.add_reaction("✋")

            pass
        elif sys.argv[1] == "edit":
            syc_message = await welcome_channel.fetch_message(SYC_MESSAGE_ID)
            await syc_message.edit(embed=syc_embed, view=syc_view)

            giveaway_message = await giveaway_channel.fetch_message(GIVEAWAY_MESSAGE_ID)
            await giveaway_message.edit(embed=giveaway_embed)

            
            print("✅ Messages edited successfully!")


        print("✅ Messages sent by SYC Bot!")
        await bot.close()
        



    
    def run_bot(bot, token):
        bot.run(token)

    
    

    ENVIRONMENT = "development" #"development"

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



        CURRENT_POOL_CHANNEL_ID = 1354449930323886266
        
        SYC_MESSAGE_ID = 000 # in welcome channel

        GIVEAWAY_MESSAGE_ID = 000 # in giveaway channel

        token = os.getenv("DISCORD_TOKEN_PROD")
        p2e_token = os.getenv("DISCORD_TOKEN_PLAY2EARN_PROD")
        
        
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

        CURRENT_POOL_CHANNEL_ID = 1354237265055842426

        SYC_MESSAGE_ID = 000 # in welcome channel

        GIVEAWAY_MESSAGE_ID = 000 # in giveaway channel
        
        token = os.getenv("DISCORD_TOKEN_DEV")
        p2e_token = os.getenv("DISCORD_TOKEN_PLAY2EARN_DEV")


    p1 = Process(target=run_bot, args=(bot, token))
    p2 = Process(target=run_bot, args=(play2earn_bot, p2e_token))
    p1.start()
    p2.start()
    p1.join()
    p2.join()


    










