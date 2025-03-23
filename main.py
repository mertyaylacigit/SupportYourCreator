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
from datetime import datetime
from discord.ext import commands
from discord.ui import Modal, TextInput, Button, View
from config import GUILD_ID, TOKEN, WELCOME_CHANNEL_ID, GIVEAWAY_CHANNEL_ID, EPIC_CLIENT_SECRET, EPIC_CLIENT_ID, EPIC_REDIRECT_URI, EPIC_OAUTH_URL
from config import send_inital_messages, TOKEN_play2earn
from config import sample_image_urls, creativeMapPlayerTimeURL, LOGGING_LEVEL, ContentCreator_name
from db_handler import db_pool, DB_DIR, initialize_key, load_user_data, restore_user_from_db, init_pg, save_dm_link_to_database, save_epic_name_to_database
from db_handler import save_image_proof_decision
from queues import RateLimitQueue, CpuIntensiveQueue
from ai import check_image
from play2earn_bot import play2earn_bot

from flask import Flask, request, redirect
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
        user_data = load_user_data(message.author.id)
        if user_data is None:
            await rate_limiter.add_request(message.channel.send, (), 
                {"content":f"❌ Please verify your Epic Games name first {message.author.mention}!\n"})
            return

        if message.attachments:
            allowed_file_types = ["image"]

            attachment = message.attachments[0]  # Nur das erste Bild verarbeiten
            for file_type in allowed_file_types:
                if file_type in attachment.content_type:
                    if file_type == "image" and user_data["step_state"] == "image_proof":
                        image_url = attachment.url

                        # ✅ Defer-Wait-Nachricht senden
                        await rate_limiter.add_request(message.channel.send, (), 
                            {"content": "⏳ Your proof is being reviewed, please wait a moment..."})

                        # ✅ Bildprüfung mit cpu_limiter (asynchron)
                        decision_future = await cpu_limiter.add_task(check_image, image_url)
                        decision = await decision_future  # ✅ Await the Future to get the actual dictionary result
                        
                        # ✅ Entscheidung speichern
                        await save_image_proof_decision(message.author.id, image_url, decision)

                        if "error" in decision:
                            embed = discord.Embed(
                                    description="❌ **Your proof has been rejected!**\n\n"
                                                f"Reason: An error occurred: {decision['error']}\n"
                                                "Please send a clear image of the message displayed in the Creative Map.",
                                    color=discord.Color.red()
                                )
                            await rate_limiter.add_request(message.channel.send, (), {"embed": embed})
                            return
                        else:
                            # ✅ Antwort an den Benutzer basierend auf der Entscheidung
                            if decision["valid_hash"]:
                                giveaway_channel = bot.get_channel(GIVEAWAY_CHANNEL_ID)
                                if user_data["points_assigned"] is None: # inital points_assigned = None so only change permission the first time
                                    await rate_limiter.add_request(giveaway_channel.set_permissions, (message.author,), {"read_messages": True})

                                time_x = 1 + decision['played_time'] / 60
                                invites_x = user_data["invite"]["total_invites"]
                                
                                embed = discord.Embed(
                                    description="**✅ Your proof has been accepted!**\n\n"
                                                f"Total playtime: **{decision['played_time']} minutes**\n"
                                                f"Your winning chance is: **{(time_x + (invites_x*1)):.2f}x** ({time_x:.2f}x by played time + {(invites_x*1):.2f}x by invites)\n\n"
                                                f"Checkout the giveaway channel: {giveaway_channel.mention}",
                                    color=discord.Color.green()
                                )
                                embed.set_footer(text="Thank you for your support! ❤️")
                                
                                guild = bot.get_guild(GUILD_ID)
                                time_role_map = {120: "Gold", 500: "Diamond", 1200: "Champion", 6000: "Unreal" }
                                last_rolename = None
                                role_name = "New"
                                for time_limit in time_role_map:
                                    if decision['played_time'] >= time_limit:
                                        last_rolename = role_name
                                        role_name = time_role_map[time_limit]

                                role = discord.utils.get(guild.roles, name=role_name)

                                if role :
                                    member = guild.get_member(message.author.id)
                                    if member is None:
                                        # Not cached, fetch from API
                                        member = await guild.fetch_member(message.author.id)
                                    
                                    if last_rolename:
                                        last_role = discord.utils.get(guild.roles, name=last_rolename)
                                        if last_role:
                                            await member.remove_roles(last_role)
                                        else:
                                            logger.warning(f"❌ Role {last_rolename} not foundin {guild.name}!")
                                    await member.add_roles(role)
                                    logger.info(f"✅ Assigned {role_name} role to {member.display_name}")
                                else:
                                    logger.warning(f"❌ {role_name} not found in {guild.name}!")
                            
                            else:
                                embed = discord.Embed(
                                    description="❌ **Your proof has been rejected!**\n\n"
                                                "Reason: Your playtime does not match the hash value.\n"
                                                "Please send a clear image of the message displayed in the Creative Map.",
                                    color=discord.Color.red()
                                )

                            await rate_limiter.add_request(message.channel.send, (), {"embed": embed})
                            return
                        

                    else:
                        await rate_limiter.add_request(message.channel.send, (), 
                            {"content": f"❌ Please verify your Epic Games name first {message.author.mention}!\n"})
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
    #await bot.tree.sync()

    
    logger.info("end Testing ✅✅✅✅✅")


    

    # Re-register the view globally after restart because the view is not registered by default after restarting the bot and not sending the view
    bot.add_view(BaseView())
    bot.add_view(Welcome2VerifyView()) 
    bot.add_view(Verify2EnterIDView(None))

    channel = bot.get_channel(WELCOME_CHANNEL_ID)

    if channel:
        if send_inital_messages:
            #UNCOMMENT THIS IF THE INTITAL MESSAGE GOT DELETED
            embed = discord.Embed(
                title="✅ Welcome to Play2Earn1v1's Verification System! ✅",
                description="Here you can submit your proofs. \nClick on **Verify** to get started!",
                color=discord.Color.blue()
            )
            view = Welcome2VerifyView()
            await channel.send(embed=embed, view=view)

    giveaway_channel = bot.get_channel(GIVEAWAY_CHANNEL_ID)

    if giveaway_channel:
        
        embed = discord.Embed(
            title="🎁 Giveaway 🎁!",
            description=(
                "\n Click on the ✋ below to **participate**!\n\n"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Thank you for your support! ❤️")

        if send_inital_messages:
            # UNCOMMENT IF GIVEAWAY MESSAGE GOT DELETED   
            giveaway_message = await giveaway_channel.send(embed=embed)
            await giveaway_message.add_reaction("✋")
            logger.info("✅⚠️ Embed sent to Giveaway channel.")

    logger.info("✅SupportYourCreator Bot is ready!")



@bot.tree.command(name="gewinnspiel", description="anzahl_gewinner Gewinner aller Supporter auslosen")
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
                print(user.name)
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
            {"content":"❌ Not enough participants to select the specified number of winners.",
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
        description=("Congratulations to the following winners:\n\n" +
                    "\n".join(f"{place+1}. {mention} 🥳" for place, mention in enumerate(winner_mentions)) +
                    "\n\n" +
                    "Winning chances for all supporters: \n"  +
                    "\n".join(f"@{user.name}: **{chance:.2f}x** winning chance" for user, chance in zip(participants, user_weights))
                    ),
        
        color=discord.Color.gold()
    )
    embed.set_footer(text="Thank you for your support! ❤️")

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
    await interaction.followup.send(f"✅ Stress test completed with frequency {frequency}", ephemeral=True)
    logger.info(f"✅⚠️Stress test started with frequency {frequency}")

@bot.tree.command(name="stresstest_cpuqueue")
async def stresstest_cpuqueue(interaction: discord.Interaction, max_workers: int):
    """Starts a stress test with the specified frequency (in seconds)."""
    # Defer response to prevent expiration
    await interaction.response.defer(thinking=True)
    await test_cpu_queue(max_workers)

    # ✅ Send the final response
    await interaction.followup.send("✅ CPU QUEUE Stress test completed ", ephemeral=True)

@bot.tree.command(name="sync2")
async def sync2(interaction: discord.Interaction):
    await bot.tree.sync()
    await interaction.response.send_message(f"✅ Slash commands synced2! commands: {await bot.tree.fetch_commands()}", ephemeral=True)
    logger.info("✅⚠️ Slash commands synced2! commands")


@bot.tree.command(name="restore_user")
async def restore_user(interaction: discord.Interaction, user: discord.Member):
    """Restores a specific user's data from PostgreSQL to the local cache."""
    user_data = await restore_user_from_db(user.id)

    if user_data:
        await interaction.response.send_message(f"✅ {user.mention} restored from database to local cache!", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ No data found for {user.mention}.", ephemeral=True)

@bot.tree.command(name="manage_roles")
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


class Welcome2VerifyView(BaseView):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        user = interaction.user

        user_data = load_user_data(user.id)
        if user_data:
            if user_data["discord_name"]:
                dm_link = user_data["dm_link"]
                await rate_limiter.add_request(interaction.response.send_message, (), 
                    {"content":f"❌ {user.mention} I have already sent you a DM! ➡️ **[Go to your DMs🔗]({dm_link})**",
                      "ephemeral":True})
                return
            
        embed = discord.Embed(
            title="Link your Epic Games Account",
            description=("Click the button below to link your Epic Games account with your Discord account "
                        "for the SupportYourCreator bot to verify your identity.\n "
                        "**The SupportYourCreator bot does NOT get access to your account data or password!**"),
            color=discord.Color.blue()
        )
        embed.set_footer(text="By linking your account, you agree that the bot may process your Epic Games username "
                              "and link it to your Discord account.")
            

        
        view = Verify2EnterIDView(user.id)
        

        dm_message = await rate_limiter.add_request(user.send, (), {"view": view, "embed": embed})
        dm_link = dm_message.jump_url
        save_dm_link_to_database(user.id, user.name, dm_link)
        await rate_limiter.add_request(interaction.response.send_message, (), 
            {"content":f"✅ {user.mention} I have sent you a DM! ➡️ **[Go to your DMs🔗]({dm_link}) **",
             "ephemeral":True})



class Verify2EnterIDView(BaseView):
    def __init__(self, discord_id):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Link Epic Games Account", style=discord.ButtonStyle.link, url=EPIC_OAUTH_URL+f"&state={discord_id}"))





# TESTS

async def simulate_user_traffic(i):
    logger.debug(f"Starting user traffic simulation for user {i}")
    
    save_epic_name_to_database(i, f"discord_name_{i}", f"epic_name_{i}")
    await asyncio.sleep(0.1)
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





# app that handles /epic_auth
discord_app = Flask(__name__)



# EPIC GAMES AUTHENTICATION

@discord_app.route('/epic_auth') 
def epic_callback():
    print("EPIC CALLBACK")
    code = request.args.get('code')
    discord_id = request.args.get('state')
    guild = bot.get_guild(int(GUILD_ID)) # BUG Potential: if guild ID changes
    print(guild, GUILD_ID)
    user = guild.get_member(int(discord_id)) 
    print(f"HERE 11: {discord_id, user, code} ")
    if user is None:
        async def fetch_user():
            user = await rate_limiter.add_request(guild.fetch_member, (int(discord_id),), {})
            return user
        user = asyncio.run(fetch_user())
        if user is None:
            logger.error("User not found")
            return "User not found, provide discord_id in request", 404
            
        
    logger.debug(f"User found (/epic_auth): {user}")

    async def exchange_code():
        print("HERE 4")
        async with aiohttp.ClientSession() as session:
            token_url = "https://api.epicgames.dev/epic/oauth/v1/token"
            data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': EPIC_REDIRECT_URI
            }
            print("HERE 5")
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
                    # BUG: if user cancels Auth, there is no key "preferred_username" but "error":"cancelled"
                    logger.debug(f"✅ Linked {discord_id} to {user_data['preferred_username']}")

                    
                    db_resp = save_epic_name_to_database(user.id, user_data['preferred_username'])

                    role = discord.utils.get(guild.roles, name="Verified")
                    
                    if role:
                        await user.add_roles(role)
                        logger.info(f"✅ Assigned verified role to {user.display_name}")
                    else:
                        logger.warning(f"❌ verified or new role not found in {guild.name}")
                    
                    # next step: image_proof
                    embed = discord.Embed(
                        title="✅ Thank you! Your Epic Games name has been verified and saved.\n"
                              "**Upload Creative Map playtime proof**",
                        description=(
                            "Please upload a **proof image** that looks like the image below. \n"
                            "You find this message inside the Play2Earn1v1 Map by pressing the UPLOAD button. \n"
                            "Take a screenshot or a clear image with your smartphone of that message and send it here!"
                        ),
                        color=discord.Color.blue()
                    )
                    logger.debug(f"✅⚠️ Epic Games Name saved: {user.id}. And Embed sent")
                    embed.set_image(url=creativeMapPlayerTimeURL)
                    embed.set_footer(text="Thank you for your support! ❤️")
                    await rate_limiter.add_request(user.send, (), 
                        {"embed": embed})
                return db_resp

    print("HERE 2")
    future = asyncio.run_coroutine_threadsafe(exchange_code(), bot.loop)
    result = future.result()
    print("HERE 3")

    return redirect("https://supportyourcreator.com/success.html")  # Redirect to Discord or another link
    
# --- END OF EPIC GAMES AUTHENTICATION ---



def run_bot(bot, token):
    bot.run(token)

### RUN FLASK SERVER AS A BACKGROUND THREAD ###
def run_discord_app():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    discord_app.run(host="0.0.0.0", port=8080, debug=True, use_reloader=False)

def run_bot_with_flask(bot, token):
    # Start Flask in a thread (same process)
    flask_thread = threading.Thread(target=run_discord_app)
    flask_thread.start()

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
    
    #discord_app_thread = threading.Thread(target=run_discord_app)
    #discord_app_thread.start()
    #bot.run(TOKEN)
    
    logger.info("✅⚠️ Flask server Discord Notify Handler started")
    logger.info("✅⚠️ Discord Bot started")

    




