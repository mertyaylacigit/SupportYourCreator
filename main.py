import discord
import os 
import sys
import shutil
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
from config import EPIC_CLIENT_SECRET, EPIC_CLIENT_ID, EPIC_REDIRECT_URI, EPIC_OAUTH_URL
from config import sample_image_urls, creativeMapPlayerTimeURL, LOGGING_LEVEL, ContentCreator_name
from db_handler import db_pool, DB_DIR, load_user_data, save_user_data, save_dm_link_to_database, save_epic_name_to_database, save_image_to_database, init_pg
from queues import RateLimitQueue

from flask import Flask, request
import threading


# ✅ Setup logging configuration
logging.basicConfig(
    level=LOGGING_LEVEL,  # Capture ALL logs (INFO, DEBUG, ERROR)  # Set to DEBUG if you want to see debug logs of discord.http's request function
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # Ensure logs are printed to Replit console
    ]
)
logger = logging.getLogger(__name__)  # ✅ Use logger instead of print()


# app that handles /notify
discord_app = Flask(__name__)



intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)
rate_limiter = RateLimitQueue(50)
logger.info("✅ created RateLimitQueue(50) succesfully!")


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
        
        # Check if the message has an attachment (image)
        if message.attachments:
            allowed_file_types = ["image"]

            # Check if the attachment is an image
            attachment = message.attachments[0]  # User should only send one image so ignore all others
            for file_type in allowed_file_types:
                if file_type in attachment.content_type:
                    if file_type == "image":
                        if user_data["step_state"] == "image_proof":
                            #logger.info(f" It is a {attachment.content_type} file.")
                            image_url = attachment.url
                            await save_image_to_database(message.author.id, image_url)
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
             
        #await rate_limiter.add_request(message.channel.send, (), 
        #    {"content":f"❌ {message.author.mention} schreibe hier bitte nichts, damit der Verlauf clean bleibt (:"})


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
                logger.info("✅ Cached giveaway message.")
        else:
            giveaway_message = bot.giveaway_message


    # Check if the reaction is the correct one (✋) and is on the giveaway message
    if str(payload.emoji) == "✋" and giveaway_message.id == payload.message_id:
        # search user inside bots cache before fetchign from API
        user = bot.get_user(payload.user_id)
        if user is None:
            logger.error("❌ User not found.")
            user = await rate_limiter.add_request(bot.fetch_user, (payload.user_id,), {})
        logger.debug(f"User found: {user}")

        if user and not user.bot:  # Ignore bot reactions
            # Load user data
            user_data = load_user_data(user.id)
            if user_data is None:
                logger.debug(f"User {user.id} not found in the database.")
                return
            # Check if the user has already reacted before
            if user_data.get("reacted_hand", False):
                logger.debug(f"User has already reacted.{user_data['reacted_hand'], user_data['discord_id']}")
                return  # User already reacted, do nothing

            # ✅ Update user data to mark them as reacted
            user_data["reacted_hand"] = True
            save_user_data(user.id, user_data)  # Save back to the database
            logger.debug(f"✅ {user.name} has reacted to the giveaway message.")

        else:
            logger.error(f"❌ User {user.id} not found.")




@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user}")
    #logger.info("🔍 Registered Slash Commands:")
    #logger.info(await bot.tree.fetch_commands())
    #await bot.tree.sync()
    #logger.info(await bot.tree.fetch_commands())

    await asyncio.sleep(1)  # ✅ Small delay before connecting to DB
    logger.info(f"✅✅✅ `db_pool` before init_pg(): {db_pool}")
    await init_pg()
    logger.info(f"✅✅✅ `db_pool` after init_pg(): {db_pool}")
    logger.info("✅ Connected to the database. ✅✅✅✅✅✅✅✅✅✅")

    asyncio.create_task(rate_limiter.worker())
    logger.info("✅ Started worker of RateLimitQueue(50) succesfully!")


    

    # Re-register the view globally after restart because the view is not registered by default after restarting the bot and not sending the view
    bot.add_view(BaseView())
    bot.add_view(Welcome2VerifyView()) 
    bot.add_view(Verify2EnterIDView(None))


    
    channel = bot.get_channel(WELCOME_CHANNEL_ID)

    if channel:
        # UNCOMMENT THIS IF THE INTITAL MESSAGE GOT DELETED
        #embed = discord.Embed(
        #    title="✅ Willkommen zum Verifizierungs-System! ✅",
        #    description=f"Hier kannst du verifizieren, dass du {ContentCreator_name} supportest. \nDrücke auf **Verifizieren**, um zu beginnen!",
        #    color=discord.Color.blue()
        #)
        #view = Welcome2VerifyView()
        #await channel.send(embed=embed, view=view)
        pass

    giveaway_channel = bot.get_channel(GIVEAWAY_CHANNEL_ID)

    if giveaway_channel:
        
        embed = discord.Embed(
            title=f"🎉 Willkommen zu {ContentCreator_name}'s Giveaway🎁!",
            description=(
                "✅ Drücke auf die Hand ✋ unten, um **teilzunehmen**!\n\n"
                "Durch TODO:CREATIVE MAP PLAYER TIME hast du eine **__1x Gewinnchance__**!\n\n"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Danke für deinen Support! ❤️")

        # UNCOMMENT IF GIVEAWAY MESSAGE GOT DELETED       # BUG: IF UNCOMMENCTING, THEN UPDATE THE MESSAGE ID IN THE GIVEAWAY.JSON FILE !!!
        #giveaway_message = await giveaway_channel.send(embed=embed)
        #await giveaway_message.add_reaction("✋")
        #logger.info("✅⚠️ Embed sent to Giveaway channel.")

        # Store the message ID in a file  # TODO: find a better solution for that
        
        #with open("giveaway.json", "w") as f:
        #    json.dump({"message_id": giveaway_message.id}, f)
        logger.info("✅Bot is ready!")


@bot.tree.command(name="gewinnspiel", description="anzahl_gewinner Gewinner aller Supporter auslosen")
async def giveaway(interaction: discord.Interaction, anzahl_gewinner: int):
    """Draw NUMBER winners from the giveaway participants."""
    if interaction.channel_id != GIVEAWAY_CHANNEL_ID:
        logger.info(f"❌ Command not allowed in channel: {interaction.channel_id}")
        return

    giveaway_channel = bot.get_channel(GIVEAWAY_CHANNEL_ID)
    if not giveaway_channel:
        logger.info(f"❌ Giveaway channel not found: {GIVEAWAY_CHANNEL_ID}")
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
    logger.info("✅ Giveaway results sent.")


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


@bot.tree.command(name="stresstest")
async def stresstest(interaction: discord.Interaction, frequency: int):
    """Starts a stress test with the specified frequency (in seconds)."""
    # Defer response to prevent expiration
    await interaction.response.defer(thinking=True)
    await stress_test_concurrent_users(frequency)

    # ✅ Send the final response
    await interaction.followup.send(f"✅ Stress test completed with frequency {frequency}")
    logger.info(f"✅⚠️Stress test started with frequency {frequency}")

@bot.tree.command(name="sync2")
async def sync2(interaction: discord.Interaction):
    await bot.tree.sync()
    await interaction.response.send_message(f"✅ Slash commands synced2! commands: {await bot.tree.fetch_commands()}")
    logger.info("✅⚠️ Slash commands synced2! commands")
    


class BaseView(View):
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)

    async def disable_buttons(self, interaction: discord.Interaction):
        """Disables all buttons and updates the message."""
        for child in self.children:  # Iterate through all buttons
            child.disabled = True

        await rate_limiter.add_request(interaction.message.edit, (), # Update the message
            {"view": self})
        logger.debug("✅⚠️ Buttons disabled.")


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
                        "für den Discord-Bot SupportYourCreator zu verknüpfen und somit deine Identität zu bestätigen.\n "
                        "**Der SupportYourCreator-Bot erhält KEINEN Zugriff auf deine Account-Daten oder dein Passwort!**"),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Mit deiner Anmeldung stimmst du zu, dass der Bot den Benutzernamen deines Epic Games Accounts "
                              "verarbeiten und mit deinen Discord-Daten verknüpfen darf.")
            

        class Verify2EnterIDView(BaseView):
            def __init__(self, discord_id):
                super().__init__(timeout=None)
                self.add_item(discord.ui.Button(label="Mit Epic Games Account verknüpfen", style=discord.ButtonStyle.link, url=EPIC_OAUTH_URL+f"&state={discord_id}"))
                
        view = Verify2EnterIDView(user.id)
        

        dm_message = await rate_limiter.add_request(user.send, (), {"view": view, "embed": embed})
        dm_link = dm_message.jump_url
        save_dm_link_to_database(user.id, dm_link)
        await rate_limiter.add_request(interaction.response.send_message, (), 
            {"content":f"✅ {user.mention} Ich habe dir eine DM geschickt! ➡️ **[Gehe zu deinen DMs🔗]({dm_link}) **",
             "ephemeral":True})








### ✅ RUN FLASK SERVER AS A BACKGROUND THREAD ###
def run_discord_app():5001
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    discord_app.run(host="0.0.0.0", port=5001, debug=True, use_reloader=False)


# TESTS

async def simulate_user_traffic(i):
    logger.debug(f"Starting user traffic simulation for user {i}")
    
    save_epic_name_to_database(i, f"discord_name_{i}", f"epic_name_{i}")
    await asyncio.sleep(0.1)
    await save_image_to_database(i, sample_image_urls[i % len(sample_image_urls)])
    await asyncio.sleep(0.1)
    

async def stress_test_concurrent_users(frequency=10):
    """Run multiple database writes concurrently."""
    logger.info(f"Starting stress test with {frequency} concurrent users")
    start_time = time.time()  # Start measuring time

    # Create tasks for multiple concurrent executions
    tasks = [simulate_user_traffic(i) for i in range(frequency)]
    await asyncio.gather(*tasks)  # Run all tasks concurrently

    end_time = time.time()  # End time
    logger.info(f"✅ Completed {frequency} tasks in {end_time - start_time:.2f} seconds!")

# --- END OF TESTS ---



# EPIC GAMES AUTHENTICATION




discord_user_epic = {}

@discord_app.route('/epic_auth')  # BUG: changed reviewerapp to discord app, so maybe port conflict
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
            logger.error("User not found")
            return "User not found, provide discord_id in request", 404
            
        
    logger.debug(f"User found (/epic_auth): {user}")

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
                #logger.info(token_data)
                end = time.time()
            
                access_token = token_data.get('access_token')
                #logger.info("got Token✅✅✅✅✅✅✅✅")

                async with session.get('https://api.epicgames.dev/epic/oauth/v1/userInfo', headers={
                    'Authorization': f'Bearer {access_token}'
                }) as user_resp:
                    user_data = await user_resp.json()
                    #logger.info(user_data)
                    logger.debug(f"✅ Linked {discord_id} to {user_data['preferred_username']}")

                    
                    db_resp = save_epic_name_to_database(user.id, user.name, user_data['preferred_username'])
                    
                    # next step: image_proof
                    embed = discord.Embed(
                        title="✅ Danke! Dein Epic Games Name wurde bestätigt und gespeichert.\n"
                              "**Creative Map Spielerzeit hochladen**",
                        description=(
                            "Bitte lade ein **Beweisbild** hoch, das zeigt, #TODO: view for creative map time played"
                        ),
                        color=discord.Color.blue()
                    )
                    logger.debug(f"✅⚠️ Epic Games Name saved: {user.id}. And Embed sent")
                    embed.set_image(url=creativeMapPlayerTimeURL)
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

    # ❌DANGER❌ DELETE local fileystem database at /data which we alse be the case when restarting the deployed bot
    if os.path.exists(DB_DIR):
        shutil.rmtree(DB_DIR)
        logger.info(f"🗑️ Deleted directory: {DB_DIR}")
    else:
        logger.info(f"❌ Directory does not exist: {DB_DIR}")
    time.sleep(1)
    os.makedirs(DB_DIR, exist_ok=True)  # reset the database


    
    # Start Flask in a separate thread
    discord_app_thread = threading.Thread(target=run_discord_app)
    discord_app_thread.start() # WARNING: dont notify when TESTING because populated discord user will end up in 400 errors of Discord API rate limit
    logger.info("✅⚠️ Flask server Discord Notify Handler started")
    
    #asyncio.run(stress_test_concurrent_users(10))

    bot.run(TOKEN)
    logger.info("✅⚠️ Discord Bot started")

    




