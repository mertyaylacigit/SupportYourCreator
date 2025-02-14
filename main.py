import discord
import os 
import json 
import asyncio
import random
import time
import logging
import aiohttp
from datetime import datetime
from discord.ext import commands
from discord.ui import Modal, TextInput, Button, View
from config import TOKEN, WELCOME_CHANNEL_ID, GIVEAWAY_CHANNEL_ID, CATEGORY_ID, GUILD_ID, FAQ_CHANNEL_ID, MERT_DISCORD_ID, TESTING_CHANNEL_ID
from config import sampleImageProofsFinalMergedURL, EPIC_CLIENT_SECRET, EPIC_CLIENT_ID, EPIC_REDIRECT_URI, EPIC_OAUTH_URL
from db_handler import load_user_data, save_user_data, save_dm_link_to_database, save_epic_name_to_database, save_image_to_database, save_video_to_database
from config import sample_image_urls, sample_video_urls
from ratelimit import RateLimitQueue, request_handler

from flask import Flask, request
import threading
from reviewGUI.app import app

logging.basicConfig(level=logging.INFO)  # Set to DEBUG if you want to see debug logs of discord.http's request function
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
rate_limiter = RateLimitQueue(50)
print("✅ created RateLimitQueue(50) succesfully!")


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if isinstance(message.channel, discord.DMChannel):
        
        user_data = load_user_data(message.author.id)
        if user_data is None:
            await rate_limiter.add_request(message.channel.send, (), 
                {"content":f"❌ Verifiziere zuerst deinen Epic Games Namen {message.author.mention}!\n"
                            "Schreibe solange hier bitte nichts, damit der unser Verlauf clean bleibt (:"})
            return
        if user_data["step_state"] == "wait":
            await rate_limiter.add_request(message.channel.send, (), 
                {"content":f"❌ Dein Beweis wird gerade geprüft {message.author.mention}.\n Wir melden uns bei dir, " 
                    "wenn wir fertig sind.\n Schreibe solange hier bitte nichts, damit der Verlauf clean bleibt (:"})
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
                            await rate_limiter.add_request(message.channel.send, (), 
                                {"embed": embed})
                            return
                        else:
                            await rate_limiter.add_request(message.channel.send, (), 
                                {"content":f"❌ {message.author.mention} Du sollst gerade kein Bild hochladen!"})
                            return
                        
                    if file_type == "video":
                        await rate_limiter.add_request(message.channel.send, (), 
                            {"content":f"❌ {message.author.mention} Du sollst kein Video hochladen! \n Falls du ein Beweisvideo "
                                "einsenden möchtest, musst du das Video auf [streamable.com](https://streamable.com) "
                                "hochladen und dann den Link hier reinsenden"})
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
            await rate_limiter.add_request(message.channel.send, (), 
                {"embed": embed})
            return
        
        # If the message is not an image or video, delete it
        #await message.delete()
        await rate_limiter.add_request(message.channel.send, (), 
            {"content":f"❌ {message.author.mention} schreibe hier bitte nichts, damit der Verlauf clean bleibt (:"})


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
                bot.giveaway_message = await rate_limiter.add_request(giveaway_channel.fetch_message, (giveaway_data["message_id"],), {})
                giveaway_message = bot.giveaway_message
                print("✅ Cached giveaway message.")
        else:
            giveaway_message = bot.giveaway_message


    # Check if the reaction is the correct one (✋) and is on the giveaway message
    if str(payload.emoji) == "✋" and giveaway_message.id == payload.message_id:
        # search user inside bots cache before fetchign from API
        user = bot.get_user(payload.user_id)
        if user is None:
            print("User not found.")
            user = await rate_limiter.add_request(bot.fetch_user, (payload.user_id,), {})
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
                    "🔸 **So lädst du das Video hoch:**\n"
                    "📎 Lade das Video auf [streamable.com](https://streamable.com) hoch und sende den Link hier rein.\n\n"
                    "**💰 100 V-Bucks = 1x Gewinnchance mehr**.\n"
                    "Wenn du ein **800 V-Bucks** Item mit dem Creator Code AMAR kaufst, erhältst du **8x Gewinnchance**!\n"
                    "Das bedeutet, du hättest eine **Gesamtgewinnchance von 9x** 🎉\n\n"
                    "❤️ **Fühl dich nicht gezwungen, etwas aus dem Item-Shop zu kaufen!**\n"
                    "Schon das Eintragen des Creator Codes **ist ein großer Support für Amar!** ❤️"
                ),
                color=discord.Color.gold()
            )
            embed.set_footer(text="Danke für deinen Support! ❤️")

            # ✅ Send the embed to the user DM
            await rate_limiter.add_request(user.send, (), 
                {"embed": embed})
            print(f"✅ Embed sent to {user.name}'s DMs.")

            # ✅ Update user data to mark them as reacted
            user_data["reacted_hand"] = True
            save_user_data(user.id, user_data)  # Save back to the database
            print(f"✅ {user.name} has reacted to the giveaway message.")

        else:
            print(f"❌ User {user.id} not found.")




@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    asyncio.create_task(rate_limiter.worker(request_handler))
    print("✅ Started worker of RateLimitQueue(50) succesfully!")


    #print("✅✅✅✅✅✅✅✅✅BEgin of Testing")
    guild = bot.get_guild(GUILD_ID)  # Replace with your server ID

    # Test rate limit queue system



    ## Send 1 message in each of the 1000 channels WITHOUT QUEUE
    #channels = [channel for category in guild.categories for channel in category.channels if channel.name.startswith("test")]
    #tasks = [channel.send(f"Test message in {channel.name}") for channel in channels]
    #print("created tasks")
    #await asyncio.sleep(3)
    #print("Now gather")
    #await asyncio.gather(*tasks)

    #embed = discord.Embed(
    #    title="Mit Epic Games Account verknüpfen",
    #    description=("Klicke auf den Button unten, um dein Epic Games Account mit deinem Discord-Account " 
    #                "für den Discord-Bot SupportAmar zu verknüpfen und somit deine Identität zu bestätigen.\n "
    #                "**Der SupportAmar-Bot erhält KEINEN Zugriff auf deine Account-Daten oder dein Passwort!**"),
    #    color=discord.Color.blue()
    #)
    #embed.set_footer(text="Mit deiner Anmeldung stimmst du zu, dass der Bot den Benutzernamen deines Epic Games Accounts "
    #                      "verarbeiten und mit deinen Discord-Daten verknüpfen darf.")
    #view = Verify2EnterIDView(0)
    ## Send 1 message in each of the 1000 channels with QUEUE using Discord API
    #channels = [channel for category in guild.categories for channel in category.channels if channel.name.startswith("test")]
    ##tasks = [rate_limiter.add_request(channel.send, (), {"content":f"Test message in {channel.name}"}) for channel in channels]
    #tasks = [rate_limiter.add_request(channel.send, (), {"embed":embed, "view":view}) for channel in channels]
    #print("created tasks")
    #await asyncio.sleep(1)
    #print("Now gather")
    #await asyncio.gather(*tasks)

    ## Send 1 message in each of the 1000 channels with QUEUE NOT using Discord API just print()
    #channels = [channel for category in guild.categories for channel in category.channels if channel.name.startswith("test")]
    #tasks = [rate_limiter.add_request(print, (f"Test message in, {channel.name}"), {}) for channel in channels]
    #print("created tasks")
    #await asyncio.sleep(1)
    #print("Now gather")
    #await asyncio.gather(*tasks)

    #print("End of testing✅✅✅✅✅✅✅✅")

    # Re-register the view globally after restart because the view is not registered by default after restarting the bot and not sending the view
    bot.add_view(BaseView())
    bot.add_view(Welcome2VerifyView()) 
    bot.add_view(Verify2EnterIDView(None))

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
        #return
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

            mert_user = await rate_limiter.add_request(bot.fetch_user, (MERT_DISCORD_ID,), {})
            faq_embed.add_field(name="**❓Du kommst nicht weiter mit deinem Problem?❓**", 
                value=f"Wenn alle Stricke reißen, dann wende dich an den Bot-Entwickler {mert_user.mention}\n\n"
                      , inline=False)
            
            #UNCOMMENT IF FAQ MESSAGE GOT DELETED
            #await rate_limiter.add_request(faq_channel.send, (), {"embed":faq_embed})
        
        embed = discord.Embed(
            title="🎉 Willkommen zu Amar's Giveaway🎁!",
            description=(
                "✅ Drücke auf die Hand ✋ unten, um **teilzunehmen**!\n\n"
                "Durch das Eintragen des Creator Codes hast du eine **__1x Gewinnchance__**!\n\n"
                "**Möchtest du deine __Gewinnchance erhöhen__?** \n➡️ Dann sende ein Beweisvideo 🎥 in den DMs von dem Bot!\n"
                "Mehr Informationen findest du in den DMs, in dem du auch das Beweisbild hochgeladen hast. \n" 
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Danke für deinen Support! ❤️")

        # UNCOMMENT IF GIVEAWAY MESSAGE GOT DELETED       # BUG: IF UNCOMMENCTING, THEN UPDATE THE MESSAGE ID IN THE GIVEAWAY.JSON FILE !!!
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
        giveaway_message = await rate_limiter.add_request(giveaway_channel.fetch_message, (giveaway_data["message_id"],), {})

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
        await rate_limiter.add_request(interaction.response.send_message, (), 
            {"content":"❌ Nicht genügend Teilnehmer, um die angegebene Anzahl von Gewinnern zu wählen.",
            "ephemeral":True})
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
                     "\n".join(f"@{user.name}: **{chance}x** Gewinnchance" for user, chance in zip(participants, user_weights))
                    ),
        
        color=discord.Color.gold()
    )
    embed.set_footer(text="Danke für deinen Support! ❤️")

    await rate_limiter.add_request(interaction.response.send_message, (), 
        {"embed": embed})


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

        await rate_limiter.add_request(interaction.message.edit, (), # Update the message
            {"view": self})


class Welcome2VerifyView(BaseView):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verifizieren", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        user = interaction.user

        user_data = load_user_data(user.id)
        if user_data:
            dm_link = user_data["dm_link"]
            await rate_limiter.add_request(interaction.response.send_message, (), 
                {"content":f"❌ {user.mention} Ich habe dir bereits eine DM geschickt! ➡️ **[Gehe zu deinen DMs🔗]({dm_link})**",
                 "ephemeral":True})
            return
            
        embed = discord.Embed(
            title="Mit Epic Games Account verknüpfen",
            description=("Klicke auf den Button unten, um dein Epic Games Account mit deinem Discord-Account " 
                        "für den Discord-Bot SupportAmar zu verknüpfen und somit deine Identität zu bestätigen.\n "
                        "**Der SupportAmar-Bot erhält KEINEN Zugriff auf deine Account-Daten oder dein Passwort!**"),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Mit deiner Anmeldung stimmst du zu, dass der Bot den Benutzernamen deines Epic Games Accounts "
                              "verarbeiten und mit deinen Discord-Daten verknüpfen darf.")
            
           
        view = Verify2EnterIDView(user.id)

        dm_message = await rate_limiter.add_request(user.send, (), {"view": view, "embed": embed})
        dm_link = dm_message.jump_url
        save_dm_link_to_database(user.id, dm_link)
        await rate_limiter.add_request(interaction.response.send_message, (), 
            {"content":f"✅ {user.mention} Ich habe dir eine DM geschickt! ➡️ **[Gehe zu deinen DMs🔗]({dm_link}) **",
             "ephemeral":True})

class Verify2EnterIDView(BaseView):
    def __init__(self, discord_id):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Mit Epic Games Account verknüpfen", style=discord.ButtonStyle.link, url=EPIC_OAUTH_URL+f"&state={discord_id}"))




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
        
    # ✅ Notify the user in their DMs
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
                f"➡️ **Bitte lade ein neues Bild hoch**, das alle Anforderungen erfüllt!"
            )
            embed.color = discord.Color.red()

    elif file_type == "video":
        if status == "approved":
            embed.title = "✅ Dein Beweisvideo wurde **akzeptiert**!"
            embed.description = (
                f"🏆 **Du hast dafür +{data['points_added']}x Gewinnchancen erhalten!** 🏆\n"
                f"🔥 Jetzt hast du insgesamt **{user_data['points_assigned']}x Gewinnchancen**, Damn! 🔥\n\n"
            )
            embed.set_footer(text="Danke für deinen Support! ❤️")
            embed.color = discord.Color.gold()
        else:
            embed.title = "❌ Dein Beweisvideo wurde **abgelehnt**!"
            faq_channel = bot.get_channel(FAQ_CHANNEL_ID)
            embed.description = (
                f"📝 Grund: {data['reason']}\n\n"
                f"➡️ **Bitte sende einen neuen [streamable.com Video Link](https://streamable.com)**, das alle Anforderungen erfüllt."
            )
            embed.color = discord.Color.red()

    # ✅ Send the embed message in the user's DMs
    asyncio.run_coroutine_threadsafe(user.send(embed=embed), bot.loop)

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



# EPIC GAMES AUTHENTICATION




discord_user_epic = {}

@reviewer_app.route('/epic_auth')
def epic_callback():
    code = request.args.get('code')
    discord_id = request.args.get('state')
    user = bot.get_user(int(discord_id))
    if user is None:
        async def fetch_user():
            user = await rate_limiter.add_request(bot.fetch_user, (int(discord_id),), {})
            return user
        user = asyncio.run(fetch_user())
        if user is None:
            print("User not found")
            
        
    print("User found (/epic_auth):", user)

    async def exchange_code():
        async with aiohttp.ClientSession() as session:
            token_url = "https://api.epicgames.dev/epic/oauth/v1/token"
            data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': EPIC_REDIRECT_URI
            }
            headers = aiohttp.BasicAuth(EPIC_CLIENT_ID, EPIC_CLIENT_SECRET)
            start = time.time()
            async with session.post(token_url, data=data, auth=headers) as resp:
                token_data = await resp.json()
                #print(token_data)
                end = time.time()
            
                access_token = token_data.get('access_token')
                #print("got Token✅✅✅✅✅✅✅✅")

                async with session.get('https://api.epicgames.dev/epic/oauth/v1/userInfo', headers={
                    'Authorization': f'Bearer {access_token}'
                }) as user_resp:
                    user_data = await user_resp.json()
                    #print(user_data)
                    print(f"✅ Linked {discord_id} to {user_data['preferred_username']}")

                    
                    db_resp = save_epic_name_to_database(user.id, user.name, user_data['preferred_username'])
                    
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
                    await rate_limiter.add_request(user.send, (), 
                        {"embed": embed})
                return db_resp

    future = asyncio.run_coroutine_threadsafe(exchange_code(), bot.loop)
    result = future.result()
    if result:   
        return "✅ Epic Games Verifizierung erfolgreich. Du kannst jetzt wieder zurück zu Discord! ✅"
    else:
        return "❌ Du hast die Epic Games Verifizierung schon abgeschlossen. Du kannst jetzt wieder zurück zu Discord! ❌"
    
# --- END OF EPIC GAMES AUTHENTICATION ---





if __name__ == "__main__":

    reviewer_app_thread = threading.Thread(target=run_reviewer_app)
    reviewer_app_thread.start()
    
    # Start Flask in a separate thread
    discord_app_thread = threading.Thread(target=run_discord_app)
    discord_app_thread.start() # WARNING: dont notify when TESTING because populated discord user will end up in 400 errors of Discord API rate limit

    #asyncio.run(stress_test_concurrent_users(10))

    bot.run(TOKEN)

    




