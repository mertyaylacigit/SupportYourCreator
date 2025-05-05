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
from multiprocessing import Process
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from config import GUILD_ID, TOKEN, GIVEAWAY_CHANNEL_ID
from config import TOKEN_play2earn, ADMIN_IDs
from config import sample_image_urls, creativeMapPlayerTimeURL, LOGGING_LEVEL #, LEADERBOARD_MESSAGE_ID
from db_handler import db_pool, DB_DIR, initialize_key, load_user_data, restore_user_from_db, init_pg, save_dm_link_to_database
from db_handler import save_image_proof_decision
from queues import RateLimitQueue, CpuIntensiveQueue
from ai import check_image
from play2earn_bot import play2earn_bot



# ✅ Setup logging configuration
logging.basicConfig(
    level=LOGGING_LEVEL,  # Capture ALL logs (INFO, DEBUG, ERROR)  # Set to DEBUG if you want to see debug logs of discord.http's request function
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # Ensure logs are printed to Replit console
    ]
)
logger = logging.getLogger(__name__)  # ✅ Use logger instead of print()




intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)



rate_limiter = RateLimitQueue(50)
logger.info("✅ created RateLimitQueue(50) succesfully!")

cpu_limiter = CpuIntensiveQueue(max_workers=1)
logger.info("✅ created CpuIntensiveQueue() succesfully!")


@bot.event
async def on_message(message):
    if message.author.bot:
        return


    if isinstance(message.channel, discord.DMChannel):
        initialize_key(message.author.id)
        user_data = load_user_data(message.author.id)

        if message.attachments:
            allowed_file_types = ["image"]

            attachment = message.attachments[0]  # Nur das erste Bild verarbeiten
            for file_type in allowed_file_types:
                if file_type in attachment.content_type:
                    if file_type == "image":
                        image_url = attachment.url

                        # ✅ Defer-Wait-Nachricht senden
                        await rate_limiter.add_request(message.channel.send, (), 
                            {"content": "⏳ Dein Nachweis wird geprüft, bitte habe einen Moment Geduld..."})

                        # ✅ Bildprüfung mit cpu_limiter (asynchron)
                        decision_future = await cpu_limiter.add_task(check_image, image_url)
                        decision = await decision_future  # ✅ Await the Future to get the actual dictionary result
                        
                        # ✅ Entscheidung speichern
                        await save_image_proof_decision(message.author.id, image_url, decision)

                        if "error" in decision:
                            embed = discord.Embed(
                                description="❌ **Dein Nachweis wurde abgelehnt!**\n\n" +
                                            f"Grund: Es ist ein Fehler aufgetreten: {decision['error']}\n" +
                                            "Bitte sende ein klares Bild der Nachricht aus der Creative Map.",
                                color=discord.Color.red()
                            )
                            await rate_limiter.add_request(message.channel.send, (), {"embed": embed})
                            return
                        else:
                            # ✅ Antwort an den Benutzer basierend auf der Entscheidung
                            if decision["valid_hash"]:
                                giveaway_channel = bot.get_channel(GIVEAWAY_CHANNEL_ID)
                                if user_data["played_minutes"] == 0: # inital played_minutes = 0 so only change permission the first time
                                    await rate_limiter.add_request(giveaway_channel.set_permissions, (message.author,), {"read_messages": True})

                                time_x = 1 + decision['played_time'] / 60
                                invites_x = user_data["invite"]["total_invites"]
                                creatorcode_x = user_data["creator_code"]
                                
                                embed = discord.Embed(
                                    description="**✅ Dein Nachweis wurde akzeptiert!**\n\n" +
                                                f"Gesamte Spielzeit: **{decision['played_time']} Minuten**\n" +
                                                f"Deine Gewinnchance: **{(time_x + (invites_x*1) + (creatorcode_x*1)):.2f}x** ({time_x:.2f}x durch Spielzeit + {(invites_x*1)}x durch Einladungen + {(creatorcode_x*1)}x durch Creator Code)\n\n" +
                                                f"**Reagiere auf das ✋ Emoji in dem Gewinnspiel-Channel: {giveaway_channel.mention}**",
                                    color=discord.Color.green()
                                )
                                embed.set_footer(text="Danke für deinen Support! ❤️")
                                
                                guild = bot.get_guild(GUILD_ID)
                                member = guild.get_member(message.author.id)
                                if member is None:
                                    # Not cached, fetch from API
                                    member = await guild.fetch_member(message.author.id)
                                time_role_map = {120: "Gold", 500: "Diamond", 1200: "Champion", 6000: "Unreal" }
                                last_rolename = "Neu"
                                role_name = "Bronze"
                                for time_limit in time_role_map:
                                    if last_rolename:
                                        last_role = discord.utils.get(member.roles, name=last_rolename)
                                        if last_role:
                                            await member.remove_roles(last_role)
                                        else:
                                            logger.debug(f"❌ {member.name} does not have last_role {last_rolename}!")
                                    if decision['played_time'] >= time_limit:
                                        last_rolename = role_name
                                        role_name = time_role_map[time_limit]

                                role = discord.utils.get(guild.roles, name=role_name)

                                if role :                                
                                    await member.add_roles(role)
                                    logger.info(f"✅ Assigned {role_name} role to {member.display_name}")
                                else:
                                    logger.warning(f"❌ {role_name} not found in {guild.name}!")
                            
                            else:
                                embed = discord.Embed(
                                    description="❌ **Dein Nachweis wurde abgelehnt!**\n\n" +
                                                "Grund: Deine Spielzeit stimmt nicht mit dem Hash-Wert überein.\n" +
                                                "Bitte sende ein klares Bild der Nachricht aus der Creative Map.",
                                    color=discord.Color.red()
                                )

                            await rate_limiter.add_request(message.channel.send, (), {"embed": embed})

                            
                            return
                        




@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user}")

    await asyncio.sleep(0.1)  # ✅ Small delay before connecting to DB
    logger.info(f"✅✅✅ `db_pool` before init_pg(): {db_pool}")
    await init_pg()
    logger.info(f"✅✅✅ `db_pool` after init_pg(): {db_pool}")
    logger.info("✅ Connected to the database. ✅✅✅✅✅✅✅✅✅✅")

    asyncio.create_task(rate_limiter.worker())
    logger.info("✅ Started worker of RateLimitQueue(50) succesfully!")

    await cpu_limiter.start_workers()
    logger.info("✅ Started worker of CpuIntensiveQueue(1) succesfully!")


    
    
    logger.info("begin Testing ✅✅✅✅✅")
    await bot.tree.sync()

    
    logger.info("end Testing ✅✅✅✅✅")


    # Re-register the view globally after restart because the view is not registered by default after restarting the bot and not sending the view
    bot.add_view(BaseView())
    bot.add_view(Welcome2SubmitView())

    

    logger.info("✅SupportYourCreator Bot is ready!")





def calculate_total_chance(played_minutes: int, invites: int, creator_code: int) -> float:
    chance = 1 + (played_minutes / 60) + invites + creator_code
    return round(chance, 2)


def is_admin_user():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.id in ADMIN_IDs
    return app_commands.check(predicate)



@bot.tree.command(name="gewinnspiel", description="anzahl_gewinner Gewinner aller Supporter auslosen")
@is_admin_user()
async def giveaway(interaction: discord.Interaction, message_id:str,  anzahl_gewinner: int):
    """Draw NUMBER winners from the giveaway participants."""
    if interaction.channel_id != GIVEAWAY_CHANNEL_ID:
        logger.info(f"❌ Command not allowed in channel: {interaction.channel_id}")
        return

    giveaway_channel = bot.get_channel(GIVEAWAY_CHANNEL_ID)
    if not giveaway_channel:
        logger.info(f"❌ Giveaway channel not found: {GIVEAWAY_CHANNEL_ID}")
        return

    
    giveaway_message = await rate_limiter.add_request(giveaway_channel.fetch_message, (int(message_id),), {})

    # TODO: REMOVE HARDCODED GIVEAWAY
    faygral = await bot.fetch_user(1352680582165037127)
    resox = await bot.fetch_user(1167383273903771668)
    
    embed = discord.Embed(
        title="🎉 Gewinner des Giveaways!",
        description=("Glückwunsch an folgende Gewinner:\n" +
                     f"\n 1. {faygral.mention} 🥳" +
                     f"\n 2. {resox.mention} 🥳"
                    ),

        color=discord.Color.gold()
    )
    embed.set_footer(text="Danke für deinen Support! ❤️")

    await rate_limiter.add_request(interaction.response.send_message, (), 
        {"embed": embed})
    logger.info("✅ Giveaway results sent.")
    return
    

    # Gather participants
    participants = []
    total_chance = 0
    user_weights = []  

    with_populated = False

    if with_populated:
        for file_name in os.listdir("data"):      # FOR USERS SAVED IN THE DABASE (FOR DEBUGGING)
            if file_name.endswith(".json"):
                file_path = os.path.join("data", file_name)
                with open(file_path, "r", encoding="utf-8") as file:
                    user_data = json.load(file)
                    if user_data:
                        chance = calculate_total_chance(user_data["played_minutes"], user_data["invite"]["total_invites"], user_data["creator_code"]) 
                        participants.append(user_data["discord_id"])
                        user_weights.append(chance)
                        total_chance += chance
    
    else: 
        for reaction in giveaway_message.reactions:    # FOR USERS THAT HAVE REACTED/ ACCESS TO GIVEAWAY
            
            async for user in reaction.users():
                print(user.name)
                if user.bot:  # Skip the bot itself
                    continue
    
                # Retrieve the user's chance from the database
                user_data = load_user_data(user.id)
                if user_data:
                    chance = calculate_total_chance(user_data["played_minutes"], user_data["invite"]["total_invites"], user_data["creator_code"]) 
                    participants.append(user_data["discord_id"])
                    user_weights.append(chance)
                    total_chance += chance

    if len(participants) < anzahl_gewinner:
        await rate_limiter.add_request(interaction.response.send_message, (), 
            {"content":"❌ Nicht genug Teilnehmer!",
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
        description=("Glückwunsch an folgende Gewinner:\n\n" +
                    "\n".join(f"{place+1}. {mention} 🥳" for place, mention in enumerate(winner_mentions)) +
                    "\n\n"
                    ),
                    # "Winning chances for all supporters: \n"  +
                    # "\n".join(f"@{user.name}: **{chance:.2f}x** winning chance" for user, chance in zip(participants, user_weights))

        
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
@is_admin_user()
async def stresstest(interaction: discord.Interaction, frequency: int):
    """Starts a stress test with the specified frequency (in seconds)."""
    # Defer response to prevent expiration
    await interaction.response.defer(thinking=True)
    await stress_test_concurrent_users(frequency)

    # ✅ Send the final response
    await interaction.followup.send(f"✅ Stress test completed with frequency {frequency}", ephemeral=True)
    logger.info(f"✅⚠️Stress test started with frequency {frequency}")

@bot.tree.command(name="stresstest_cpuqueue")
@is_admin_user()
async def stresstest_cpuqueue(interaction: discord.Interaction, max_workers: int):
    """Starts a stress test with the specified frequency (in seconds)."""
    # Defer response to prevent expiration
    await interaction.response.defer(thinking=True)
    await test_cpu_queue(max_workers)

    # ✅ Send the final response
    await interaction.followup.send("✅ CPU QUEUE Stress test completed ", ephemeral=True)

@bot.tree.command(name="sync2")
@is_admin_user()
async def sync2(interaction: discord.Interaction):
    await bot.tree.sync()
    await interaction.response.send_message(f"✅ Slash commands synced2! commands: {await bot.tree.fetch_commands()}", ephemeral=True)
    logger.info("✅⚠️ Slash commands synced2! commands")


@bot.tree.command(name="restore_user")
@is_admin_user()
async def restore_user(interaction: discord.Interaction, user: discord.Member):
    """Restores a specific user's data from PostgreSQL to the local cache."""
    user_data = await restore_user_from_db(user.id)

    if user_data:
        await interaction.response.send_message(f"✅ {user.mention} restored from database to local cache!", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ No data found for {user.mention}.", ephemeral=True)

@bot.tree.command(name="manage_roles")
@is_admin_user()
async def manage_roles(interaction: discord.Interaction, mode: str, user: discord.Member, role: discord.Role):

    if mode == "add":
        await user.add_roles(role)
        await interaction.response.send_message(f"✅ Added role {role.name} to {user.mention}", ephemeral=True)
    elif mode == "remove":
        await user.remove_roles(role)
        await interaction.response.send_message(f"✅ Removed role {role.name} from {user.mention}", ephemeral=True)
    


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


class Welcome2SubmitView(BaseView):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Beweis senden", style=discord.ButtonStyle.green, custom_id="submit_button")
    async def send_proof(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        user = interaction.user

        initialize_key(user.id)
        user_data = load_user_data(user.id)
            
        embed = discord.Embed(
            title="**Lade deinen Nachweis der Spielzeit von der Play2Earn Map hoch**",
            description=(
                "Bitte lade ein **Beweisbild** hoch, das wie das unten gezeigte Bild aussieht. \n"
                "Du findest diese Nachricht in der Play2Earn1v1 Map, indem du den SUBMIT-Button drückst. \n"
                "Mache einen Screenshot oder ein klares Foto dieser Nachricht mit deinem Smartphone und sende es hier rein!"
            ),
            color=discord.Color.blue()
        )
        embed.set_image(url=creativeMapPlayerTimeURL)
        
        

        dm_message = await rate_limiter.add_request(user.send, (), {"embed": embed})
        dm_link = dm_message.jump_url
        save_dm_link_to_database(user.id, user.name, dm_link)
        await rate_limiter.add_request(interaction.response.send_message, (), 
            {"content":f"✅ {user.mention} Ich habe dir eine DM gesendet! ➡️ **[Zu deinen DMs🔗]({dm_link}) **",
             "ephemeral":True})






# TESTS

async def simulate_user_traffic(i):
    logger.debug(f"Starting user traffic simulation for user {i}")
    
    #await save_image_to_database(i, sample_image_urls[i % len(sample_image_urls)])
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

async def test_cpu_queue(max_workers=1):

    cpu_limiterTEST = CpuIntensiveQueue(max_workers=max_workers)
    logger.info("✅ created CpuIntensiveQueue() succesfully!")
    await cpu_limiterTEST.start_workers()
    logger.info("✅ Started worker of CpuIntensiveQueue() succesfully!")
    
    testing_starttime = time.time()

    image_tasks = [
        cpu_limiterTEST.add_task(check_image, i) for i in range(1,8) for j in range(4)
    ]
    results = await asyncio.gather(*image_tasks)  # Wait for all tasks to finish

    # Print results
    for res in results:
        print(res)



    testing_endtime = time.time()
    logger.info(f"⏰Testing Time: {testing_endtime - testing_starttime}")

# --- END OF TESTS ---











def run_bot(bot, token):
    bot.run(token)

### RUN FLASK SERVER AS A BACKGROUND THREAD ###
def run_discord_app():
    # app that handles /epic_auth
    discord_app = Flask(__name__)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    discord_app.run(host="0.0.0.0", port=8080, debug=True, use_reloader=False)

def run_bot_with_flask(bot, token):
    ## Start Flask in a thread (same process)
    #flask_thread = threading.Thread(target=run_discord_app)
    #flask_thread.start()

    # Start the Discord bot (blocks until closed)
    bot.run(token)


if __name__ == "__main__":

    # ❌DANGER❌ DELETE local fileystem database at /data which we alse be the case when restarting the deployed bot
    if os.path.exists(DB_DIR):
        shutil.rmtree(DB_DIR)
        logger.info(f"🗑️ Deleted directory: {DB_DIR}")
    else:
        logger.info(f"❌ Directory does not exist: {DB_DIR}")
    time.sleep(0.1)
    os.makedirs(DB_DIR, exist_ok=True)  # reset the database


    
    
    #asyncio.run(stress_test_concurrent_users(10))

    p1 = Process(target=run_bot_with_flask, args=(bot, TOKEN))
    p2 = Process(target=run_bot, args=(play2earn_bot, TOKEN_play2earn))
    p1.start()
    p2.start()
    
    
    logger.info("✅⚠️ Flask server Discord Notify Handler started")
    logger.info("✅⚠️ Discord Bot started")

    




