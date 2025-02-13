import discord
import os 
import json 
import asyncio
import random
import time
import logging
from datetime import datetime
from discord.ext import commands
from discord.ui import Modal, TextInput, Button, View
from config import TOKEN, WELCOME_CHANNEL_ID, GIVEAWAY_CHANNEL_ID, CATEGORY_ID, GUILD_ID, FAQ_CHANNEL_ID, MERT_DISCORD_ID, TESTING_CHANNEL_ID
from config import sampleImageProofsFinalMergedURL
from db_handler import load_user_data, save_user_data, save_epic_name_to_database, save_image_to_database, save_video_to_database
from config import sample_image_urls, sample_video_urls

from flask import Flask, request
import threading
from reviewGUI.app import app

logging.basicConfig(level=logging.DEBUG)  # Enable INFO logging
# app that handles /notify
discord_app = Flask(__name__)

# Flask app that handles the reviewer webserver
reviewer_app = app

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if isinstance(message.channel, discord.Thread) and message.channel.type == discord.ChannelType.private_thread:
        # check if message is in SupportAmar category/context
        parent_channel = message.channel.parent
        if parent_channel.category and parent_channel.category.id != CATEGORY_ID:
            return

        user_data = load_user_data(message.author.id)
        if user_data is None:
            await message.channel.send(f"❌ Verifiziere zuerst deinen Epic Games Namen {message.author.mention}!\n"
                                       "Schreibe solange hier bitte nichts, damit der Verlauf clean bleibt (:") # erst danach wird ein user entry erstellt
            return
        if user_data["step_state"] == "wait":
            await message.channel.send(f"❌ Dein Beweis wird gerade geprüft {message.author.mention}.\n Wir melden uns bei dir, " 
                                       "wenn wir fertig sind.\n Schreibe solange hier bitte nichts, damit der Verlauf clean bleibt (:")
            return
        
        # Check if the message has an attachment (image/video)
        if message.attachments:
            allowed_file_types = ["image", "video"]

            # Check if the attachment is an image or video
            attachment = message.attachments[0]  # User should only send one image/video so ignore all others
            for file_type in allowed_file_types:
                if file_type in attachment.content_type:
                    if file_type == "image":
                        if user_data["step_state"] == "image_proof":
                            #print(f" It is a {attachment.content_type} file.")
                            image_url = attachment.url
                            save_image_to_database(message.author.id, image_url)
                             #✅ Send confirmation message
                            embed = discord.Embed(
                                description="⏳ **Wir werden dein Beweisbild prüfen und uns eigenständig bei dir melden.**\n\n"
                                            "✅ **Du musst nichts mehr machen!**",
                                color=discord.Color.green()
                            )
                            embed.set_footer(text="Danke für deine Geduld! ❤️")
                            await message.channel.send(embed=embed)
                            return
                        else:
                            await message.channel.send(f"❌ {message.author.mention} Du sollst gerade kein Bild hochladen!")
                            return
                        
                    if file_type == "video":
                        await message.channel.send(f"❌ {message.author.mention} Du sollst kein Video hochladen! \n Falls du ein Beweisvideo "
                                                   "einsenden möchtest, musst du das Video auf [streamable.com](https://streamable.com) "
                                                   "hochladen und dann den Link hier reinsenden")
                        return
        # check if message is the URL Link to the uploaded video on streamable.com
        if "streamable.com" in message.content:
            #print(f" It is a {attachment.content_type} file. TODO: video handling")
            streamable_video_url = message.content
            save_video_to_database(message.author.id, streamable_video_url)
            #✅ Send confirmation message
            embed = discord.Embed(
                description="⏳ **Wir werden dein Beweisvideo 🎥 prüfen und uns eigenständig bei dir melden.**\n\n"
                            "✅ **Du musst nichts mehr machen!**",
                color=discord.Color.green()
            )
            embed.set_footer(text="Danke für deine Geduld! ❤️")
            await message.channel.send(embed=embed)
            return
        
        # If the message is not an image or video, delete it
        #await message.delete()
        await message.channel.send(f"❌ {message.author.mention} schreibe hier bitte nichts, damit der Verlauf clean bleibt (:")


@bot.event
async def on_raw_reaction_add(payload):
    """Triggered when a user reacts to the giveaway message for the first time."""

    # Check if the reaction is in the giveaway channel
    if payload.channel_id != GIVEAWAY_CHANNEL_ID:
        return  # Ignore reactions in other channels

    # Fetch the giveaway message (if needed)
    giveaway_channel = bot.get_channel(GIVEAWAY_CHANNEL_ID)
    with open("giveaway.json", "r") as f:
        giveaway_data = json.load(f)
        # caching the giveaway message inside the bot to avoid fetching it multiple times with Discord API
        if not hasattr(bot, "giveaway_message"):
            if giveaway_channel:
                bot.giveaway_message = await giveaway_channel.fetch_message(giveaway_data["message_id"])  # API call
                giveaway_message = bot.giveaway_message
                print("✅ Cached giveaway message.")
        else:
            giveaway_message = bot.giveaway_message


    # Check if the reaction is the correct one (✋) and is on the giveaway message
    if str(payload.emoji) == "✋" and giveaway_message.id == payload.message_id:
        # search user inside bots cache before fetchign from API
        user = bot.get_user(payload.user_id)
        print("User found by get_user:", user)
        if user is None:
            print("User not found.")
            user = await bot.fetch_user(payload.user_id)
        print("User found:", user)

        if user and not user.bot:  # Ignore bot reactions
            # Load user data
            user_data = load_user_data(user.id)
            if user_data is None:
                print(f"User {user.id} not found in the database.")
                return
            # Check if the user has already reacted before
            if user_data.get("reacted_hand", False):
                print(f"User has already reacted.{user_data['reacted_hand'], user_data['discord_id']}")
                return  # User already reacted, do nothing
            
            # ✅ Find the user's verification thread
            verification_channel = bot.get_channel(WELCOME_CHANNEL_ID)
            user_thread = discord.utils.get(verification_channel.threads, name=f"{user.name.lower()}-verifizierung")
            if user_thread:
                # ✅ Create the embed message
                embed = discord.Embed(
                    title="🎁 Möchtest du deine Gewinnchance erhöhen? 🎁",
                    description=(
                        "Dann sende hier ein **Beweisvideo 🎥**, "
                        "das zeigt, wie du etwas aus dem **Item-Shop mit dem Creator Code AMAR kaufst.**\n\n"
                        "🔹 **Das Video muss Folgendes zeigen:**\n"
                        "1️⃣ Der **Creator Code AMAR** muss sichtbar sein.\n"
                        "2️⃣ Dein **Epic Games Name** muss zu sehen sein.\n"
                        "3️⃣ Der **gesamte Kaufvorgang** bis zum Ende muss im Video sein.\n"
                        "4️⃣ Am Ende musst du die Items ausrüsten, um zu beweisen, dass du den **Kauf nicht zurückerstattest**.\n\n"
                        "➡️ **So sollte dein Beweisvideo ungefähr aussehen: [Muster Video](https://streamable.com/cnsugr)** "
                        "**(unbedingt anschauen, damit dein Video garantiert akzeptiert wird!)**\n\n"
                        "🔸 So lädst du das Video hoch:\n"
                        "📎 Lade das Video auf [streamable.com](https://streamable.com) hoch und sende den Link hier rein.\n\n"
                        "**💰 100 V-Bucks = 1x Gewinnchance mehr**.\n"
                        "Wenn du ein **800 V-Bucks** Item mit dem Creator Code AMAR kaufst, erhältst du **8x Gewinnchance**!\n"
                        "Das bedeutet, du hättest eine **Gesamtgewinnchance von 9x** 🎉\n\n"
                        "❤️ **Fühl dich nicht gezwungen, etwas aus dem Item-Shop zu kaufen!**\n"
                        "Schon das Eintragen des Creator Codes **ist ein großer Support für Amar!** ❤️"
                    ),
                    color=discord.Color.gold()
                )

                # ✅ Send the embed to the user's verification thread
                await user_thread.send(embed=embed)
                print(f"✅ Embed sent to {user.name}'s verification thread.")

            else:
                print(f"❌ Verification thread not found for {user.name}.")

            # ✅ Update user data to mark them as reacted
            user_data["reacted_hand"] = True
            save_user_data(user.id, user_data)  # Save back to the database
            print(f"✅ {user.name} has reacted to the giveaway message.")

        else:
            print(f"❌ User {user.id} not found.")




@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")


    print("End of testing")

    # Re-register the view globally after restart because the view is not registered by default after restarting the bot and not sending the view
    bot.add_view(BaseView())
    bot.add_view(Welcome2VerifyView()) 
    bot.add_view(Verify2EnterIDView())

    ## sync for commands           #BUG/WARNING: this sync command took long and sometimes didnt terminate ending it rate limit ban...
    #try:                          #DOCUMENTATION: ...and it is also working without it
    #    synced = await bot.tree.sync()
    #    print(f"✅ Synced {len(synced)} commands: {synced}")
    #except Exception as e:
    #    print(f"❌ Error syncing commands: {e}")   

    
    channel = bot.get_channel(WELCOME_CHANNEL_ID)

    if channel:
        # Purge all threads in the channel (only for development)
        #for thread in channel.threads:
        #    try:
        #        await thread.delete()
        #        print(f"🗑️ Thread gelöscht: {thread.name}")
        #    except Exception as e:
        #        print(f"❌ Konnte den Thread {thread.name} nicht löschen: {e}")

        #await channel.purge()

        # UNCOMMENT THIS IF THE INTITAL MESSAGE GOT DELETED
        #embed = discord.Embed(
        #    title="✅ Willkommen zum Verifizierungs-System! ✅",
        #    description="Hier kannst du verifizieren, dass du Amar supportest. \nDrücke auf **Verifizieren**, um zu beginnen!",
        #    color=discord.Color.blue()
        #)
        #view = Welcome2VerifyView()
        #await channel.send(embed=embed, view=view)
        pass

    giveaway_channel = bot.get_channel(GIVEAWAY_CHANNEL_ID)

    if giveaway_channel:
        #await giveaway_channel.purge()  # Clear previous messages (optional

        faq_channel = bot.get_channel(FAQ_CHANNEL_ID)
        if faq_channel:
            #DONT PURGE BUT DELETE MANUALLY
            #await faq_channel.purge()
            faq_embed = discord.Embed(
                title="SupportAmar FAQ",
                description="Hier findest du oft gestellte Fragen:\n",
                color=discord.Color.blue()
            )
            #faq_embed.add_field(name=" ", value=" ", inline=False)
            #faq_embed.add_field(name="**🎁Möchtest du deine Gewinnchance erhöhen?🎁**",
            #    value="Dann sende in dem vorherigen Bot Channel ein Beweisvideo 🎥!\n"
            #          "Mehr Informationen findest du in dem Bot Channel, in dem du auch das Beweisbild hochgeladen hast.\n",
            #          inline=False)
            #faq_embed.add_field(name=" ", value=" ", inline=False)
            # Abgrenzung
            faq_embed.add_field(name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", value=" ", inline=False)
            faq_embed.add_field(name=" ", value=" ", inline=False)
            faq_embed.add_field(name="**🕐Ich habe den Beweis hochgeladen, aber es tut sich nichts?🕐**", 
                                value="Keine Sorge, wir werden uns schnellstmöglich bei dir melden. Gib uns etwas Zeit, "
                                "wir machen auch mal Pausen (; \n Du musst nichts mehr machen! Checke später nochmal, ob wir fertig sind.\n\n"
                                , inline=False)
            faq_embed.add_field(name=" ", value=" ", inline=False)
            # Abgrenzung
            #faq_embed.add_field(name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", value=" ", inline=False)
            #
            #faq_embed.add_field(name=" ", value=" ", inline=False)
            #faq_embed.add_field(name="**📁Video Datei ist zu groß?📁**", 
            #    value="Discord erlaubt nur maximal 100MB große Dateien hochzuladen. \n"
            #          "Wenn du das Kauf Video schon aufgenommen hast, ist das kein Problem! \n"
            #          "Nutze ein Software Tool deiner Wahl, um die Video Datei zu verkleinern. "
            #          "Meistens sind die Videos in hoher Auflösung. Wenn du die Auflösung von 1080p auf 360p "
            #          "runterschraubst, verkleinert das die Datei schon sehr. Achte darauf, dass die Anforderungen "
            #          "immernoch erfüllt sind."
            #    , inline=False)
            #faq_embed.add_field(name=" ", value=" ", inline=False)
            # Abgrenzung
            faq_embed.add_field(name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", value=" ", inline=False)
            faq_embed.add_field(name=" ", value=" ", inline=False)
        
            mert_user = await bot.fetch_user(MERT_DISCORD_ID)
            faq_embed.add_field(name="**❓Du kommst nicht weiter mit deinem Problem?❓**", 
                value=f"Wenn alle Stricke reißen, dann wende dich an den Bot-Entwickler {mert_user.mention}\n\n"
                      , inline=False)
            
            #UNCOMMENT IF FAQ MESSAGE GOT DELETED
            #await faq_channel.send(embed=faq_embed)
        
        embed = discord.Embed(
            title="🎉 Willkommen zu Amar's Giveaway🎁!",
            description=(
                "✅ Drücke auf die Hand ✋ unten, um **teilzunehmen**!\n\n"
                "Durch das Eintragen des Creator Codes hast du eine **__1x Gewinnchance__**!\n\n"
                "**Möchtest du deine __Gewinnchance erhöhen__?** \n➡️ Dann sende in dem vorherigen Bot Channel ein Beweisvideo 🎥!\n"
                "Mehr Informationen findest du in dem Bot Channel, in dem du auch das Beweisbild hochgeladen hast. \n" 
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Danke für deinen Support! ❤️")

        # UNCOMMENT IF GIVEAWAY MESSAGE GOT DELETED
        #giveaway_message = await giveaway_channel.send(embed=embed)
        #await giveaway_message.add_reaction("✋")

        # Store the message ID in a file
        
        #with open("giveaway.json", "w") as f:
        #    json.dump({"message_id": giveaway_message.id}, f)
        print("Bot is ready!")


@bot.tree.command(name="gewinnspiel", description="anzahl_gewinner Gewinner aller Supporter auslosen")
async def giveaway(interaction: discord.Interaction, anzahl_gewinner: int):
    """Draw NUMBER winners from the giveaway participants."""
    if interaction.channel_id != GIVEAWAY_CHANNEL_ID:
        print(f"❌ Command not allowed in channel: {interaction.channel_id}")
        return

    giveaway_channel = bot.get_channel(GIVEAWAY_CHANNEL_ID)
    if not giveaway_channel:
        print(f"❌ Giveaway channel not found: {GIVEAWAY_CHANNEL_ID}")
        return

    with open("giveaway.json", "r") as f:
        giveaway_data = json.load(f)
        giveaway_message = await giveaway_channel.fetch_message(giveaway_data["message_id"])

    # Gather participants
    participants = []
    total_points = 0
    user_weights = []  

    with_populated = False

    if with_populated:
        for file_name in os.listdir("data"):      # FOR USERS SAVED IN THE DABASE (FOR DEBUGGING)
            if file_name.endswith(".json"):
                file_path = os.path.join("data", file_name)
                with open(file_path, "r", encoding="utf-8") as file:
                    user_data = json.load(file)
                    if user_data and user_data.get("points_assigned"):
                        points = user_data["points_assigned"]
                        participants.append(user_data["discord_id"])
                        user_weights.append(points)
                        total_points += points
    
    else:
        for reaction in giveaway_message.reactions:    # FOR USERS THAT HAVE REACTED/ ACCESS TO GIVEAWAY
            async for user in reaction.users():
                if user.bot:  # Skip the bot itself
                    continue
    
                # Retrieve the user's points_assigned from the database
                user_data = load_user_data(user.id)
                if user_data and user_data.get("points_assigned"):
                    points = user_data["points_assigned"]
                    participants.append(user)
                    user_weights.append(points)
                    total_points += points

    if len(participants) < anzahl_gewinner:
        await interaction.response.send_message(
            "❌ Nicht genügend Teilnehmer, um die angegebene Anzahl von Gewinnern zu wählen.",
            ephemeral=True
        )
        return

    # Select winners using weighted random sampling
    winners = weighted_random_selection(participants, user_weights, anzahl_gewinner)

    # Prepare the results
    if with_populated:
        winner_mentions = [winner for winner in winners] 
    else:
        winner_mentions = [winner.mention for winner in winners]
    embed = discord.Embed(
        title="🎉 Gewinner des Giveaways!",
        description=("Herzlichen Glückwunsch an die folgenden Gewinner:\n\n" +
                     "\n".join(f"{place+1}. {mention} 🥳" for place, mention in enumerate(winner_mentions)) +
                     "\n\n" +
                     "Gewinnchancen aller Supporter: \n"  +
                     "\n".join(f"@{user.name}: {chance}x Gewinnchance" for user, chance in zip(participants, user_weights))
                    ),
        
        color=discord.Color.gold()
    )
    embed.set_footer(text="Danke für deinen Support! ❤️")

    await interaction.response.send_message(embed=embed)


def weighted_random_selection(participants, user_weights, num_winners):
    """
    Selects winners from participants based on weighted probability without replacement.

    :param participants: List of participant Discord user IDs.
    :param user_weights: Dictionary mapping user IDs to their weights (points assigned).
    :param num_winners: Number of winners to select.
    :return: List of selected winner IDs.
    """

    selected_winners = []
    remaining_participants = participants.copy()
    remaining_weights = user_weights.copy()

    for _ in range(num_winners):
        if not remaining_participants:
            break  # Stop if there are no more participants

        # Select one winner based on their weight (probability)
        winner = random.choices(remaining_participants, weights=remaining_weights, k=1)[0]
        selected_winners.append(winner)

        # Remove the selected winner and their weight
        index = remaining_participants.index(winner)
        remaining_participants.pop(index)
        remaining_weights.pop(index)

    return selected_winners

    


class BaseView(View):
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)

    async def disable_buttons(self, interaction: discord.Interaction):
        """Disables all buttons and updates the message."""
        for child in self.children:  # Iterate through all buttons
            child.disabled = True

        await interaction.message.edit(view=self)  # Update the message


class Welcome2VerifyView(BaseView):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verifizieren", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        user = interaction.user
        channel = guild.get_channel(WELCOME_CHANNEL_ID)

        existing_thread = discord.utils.get(channel.threads, name=f"{user.name.lower()}-verifizierung")
        if existing_thread:
            await interaction.response.send_message(
                f"❌ Du hast bereits ein offenes Ticket: {existing_thread.mention}",
                ephemeral=True
            )
            return

        thread = await channel.create_thread(            # PROBLEM: creating threads is rate limited to 50 per 300 seconds 
            name=f"{user.name.lower()}-verifizierung",   # TODO: change this to sending the message in DM rather than in private thread
            type=discord.ChannelType.private_thread,
            invitable=False
        )
        await thread.add_user(user)
        embed = discord.Embed(
            title="🔑 Epic Games Verifizierung",
            description="Drücke auf den Button unten, um deinen Epic Games Namen einzugeben!",
            color=discord.Color.blue()
        )
        view = Verify2EnterIDView()

        await thread.send(embed=embed, view=view)

        await interaction.response.send_message(f"✅ Dein privates Ticket wurde erstellt: ➡️ **{thread.mention}**", ephemeral=True)


class Verify2EnterIDView(BaseView):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎮 Epic Games Namen eingeben", style=discord.ButtonStyle.blurple, custom_id="enter_epic_id")
    async def enter_epic_id(self, interaction: discord.Interaction, button: Button):
        print(interaction.channel, interaction.user, self, self.children)
        await interaction.response.send_modal(EpicIDModal(interaction.channel, interaction.user, self))


class EpicIDModal(Modal):
    def __init__(self, thread, user, parent_view):
        super().__init__(title="Gib deinen Epic Games Namen ein")
        self.thread = thread
        self.user = user
        self.parent_view = parent_view
        self.text = TextInput(
            label="Gib dein Epic Games Namen ein!",
            placeholder="z.B. EpicGamer123",
            required=True
        )
        self.add_item(self.text)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        epic_name = str(self.text.value)
        save_epic_name_to_database(self.user.id, self.user.name, epic_name)

        # Disable the buttons after clicking
        await self.parent_view.disable_buttons(interaction)

        # next step: proof code registration
        embed = discord.Embed(
            title="✅ Danke! Dein Epic Games Name wurde bestätigt und gespeichert.\n"
                  "**Creator Code AMAR eingetragen?**",
            description=(
                "Bitte lade ein **Beweisbild** hoch, das zeigt, dass du den Creator Code **AMAR** benutzt hast:\n\n" 
                "🔹 **Das Bild sollte Folgendes zeigen:**\n"
                "1️⃣ Dein **Epic Games Name**\n"
                "2️⃣ Den eingetragenen Creator Code **AMAR**\n\n"
                "🔸 **Möglichkeiten zur Erstellung des Beweisbildes:**\n\n"
                "**🎮 Option 1: Direkt im Fortnite-Spiel**\n"
                "1️⃣ Öffne Fortnite und gehe in den **Item-Shop**.\n"
                "2️⃣ Trage den Creator Code **AMAR** unten rechts im Shop ein.\n"
                "3️⃣ Mach einen Screenshot oder fotografiere den Bildschirm (z.B. mit dem Handy).\n\n"
                "**🖥️ Option 2: Über die Fortnite-Website**\n"
                "1️⃣ Gehe auf [fortnite.com/item-shop](https://www.fortnite.com/item-shop) und logge dich ein.\n"
                "2️⃣ Klicke oben rechts auf den **Creator Code Button** [★] und gib **AMAR** ein.\n"
                "3️⃣ Mache einen Screenshot oder fotografiere den Bildschirm. (z.B. mit dem Handy)\n\n"
                "🔸 **So lädst du das Bild hoch:**\n"
                "📎 Drücke hier im Discord Bot-Chat unten links auf das **(+)** Symbol und lade das Bild hoch.\n\n"
                "➡️ **So sollte dein Beweisbild aussehen (eins von beiden Optionen und ohne Markierungen):**"
            ),
            color=discord.Color.blue()
        )
        embed.set_image(url=sampleImageProofsFinalMergedURL)
        embed.set_footer(text="Vielen Dank für deinen Support! ❤️")
        await self.thread.send(embed=embed)



### ✅ FLASK API FOR REVIEWER ###
@discord_app.route("/notify", methods=["POST"])
def notify():
    """Handles notifications from the reviewer webserver."""
    data = request.json
    discord_id = int(data["discord_id"])
    file_type = data["file_type"]
    status = data["status"]

    guild = bot.get_guild(GUILD_ID)
    user = guild.get_member(discord_id)

    user_data = load_user_data(discord_id)

    if not user:
        return {"error": "User not found"}, 404

    # Find the user's verification thread
    verification_channel = bot.get_channel(WELCOME_CHANNEL_ID)
    user_thread = discord.utils.get(verification_channel.threads, name=f"{user.name.lower()}-verifizierung")
    
    if not user_thread:
        return {"error": "Thread not found"}, 404
        
    # ✅ Notify the user in their private verification thread
    embed = discord.Embed(color=discord.Color.blue())

    if file_type == "image":
        if status == "approved":
        
            giveaway_channel = bot.get_channel(GIVEAWAY_CHANNEL_ID)
            if giveaway_channel:
                embed.title = "✅ Dein Beweisbild wurde **akzeptiert**!"
                embed.description = (
                    "✨ **Du hast jetzt Zugang zum Giveaway-Channel!**\n"
                    f"➡️ **Gehe zum Giveaway-Kanal:** {giveaway_channel.mention}"
                )
                embed.set_footer(text="Danke für deinen Support! ❤️")
                embed.color = discord.Color.green()
                # ✅ Grant access to the Giveaway Channel
                asyncio.run_coroutine_threadsafe(giveaway_channel.set_permissions(user, read_messages=True), bot.loop)

        elif status == "denied":
            embed.title = "❌ Dein Beweisbild wurde **abgelehnt**"
            faq_channel = bot.get_channel(FAQ_CHANNEL_ID)
            embed.description = (
                f"📝 Grund: {data['reason']}\n\n"
                f"➡️ **Bitte lade ein neues Bild hoch**, das alle Anforderungen erfüllt! ➡️{faq_channel.mention}"
            )
            embed.color = discord.Color.red()

    elif file_type == "video":
        if status == "approved":
            embed.title = "✅ Dein Beweisvideo wurde **akzeptiert**!"
            embed.description = (
                f"🏆 **Du hast dafür +{data['points_added']}x Gewinnchancen erhalten!** 🏆\n"
                f"🔥 Jetzt hast du insgesamt **{user_data['points_assigned']}x Gewinnchancen**, Damn! 🔥\n\n"
                "🔔 **Je mehr Support, desto höher deine Gewinnchance!** 🔔\n"
            )
            embed.set_footer(text="Danke für deinen Support! ❤️")
            embed.color = discord.Color.gold()
        else:
            embed.title = "❌ Dein Beweisvideo wurde **abgelehnt**!"
            faq_channel = bot.get_channel(FAQ_CHANNEL_ID)
            embed.description = (
                f"📝 Grund: {data['reason']}\n\n"
                f"➡️ **Bitte lade ein neues Video hoch**, das alle Anforderungen erfüllt. ➡️ {faq_channel.mention}"
            )
            embed.color = discord.Color.red()

    # ✅ Send the embed message in the user's verification thread
    asyncio.run_coroutine_threadsafe(user_thread.send(embed=embed), bot.loop)

    return {"success": True}


### ✅ RUN FLASK SERVER AS A BACKGROUND THREAD ###
def run_reviewer_app():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    reviewer_app.run(host="0.0.0.0", port=8080, debug=True, use_reloader=False)
    
def run_discord_app():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    discord_app.run(host="0.0.0.0", port=5001, debug=True, use_reloader=False)


# TESTS

async def simulate_user_traffic(i):
    print(f"Starting user traffic simulation for user {i}")
    
    save_epic_name_to_database(i, f"discord_name_{i}", f"epic_name_{i}")
    save_image_to_database(i, sample_image_urls[i % len(sample_image_urls)])
    save_video_to_database(i,sample_video_urls[i % len(sample_video_urls)])

async def stress_test_concurrent_users(frequency=10):
    """Run multiple database writes concurrently."""
    start_time = time.time()  # Start measuring time

    # Create tasks for multiple concurrent executions
    tasks = [simulate_user_traffic(i) for i in range(frequency)]
    await asyncio.gather(*tasks)  # Run all tasks concurrently

    end_time = time.time()  # End time
    print(f"✅ Completed {frequency} tasks in {end_time - start_time:.2f} seconds!")



# --- END OF TESTS ---

if __name__ == "__main__":

    reviewer_app_thread = threading.Thread(target=run_reviewer_app)
    reviewer_app_thread.start()
    
    # Start Flask in a separate thread
    discord_app_thread = threading.Thread(target=run_discord_app)
    discord_app_thread.start() # WARNING: dont notify when TESTING because populated discord user will end up in 400 errors of Discord API rate limit

    #asyncio.run(stress_test_concurrent_users(10))
    
    bot.run(TOKEN)

    # Run the test

