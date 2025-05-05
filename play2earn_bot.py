import discord
from discord.ext import tasks
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
from config import LEADERBOARD_CHANNEL_ID, LEADERBOARD_MESSAGE_ID, LOGGING_LEVEL, INVITE_CHANNEL_ID, MEMBERS_STATS_ID, MINUTES_PLAYED_ID,  PRICE_POOL_ID, GUILD_ID
from db_handler import load_user_data, save_invite_join_to_database, save_invite_remove_to_database, restore_invite_user_map, init_pg
from db_handler import get_leaderboard_top_users

# DANGER: TODO For scalability: Here I dont use API rate limiter 

# ✅ Setup logging configuration
logging.basicConfig(
    level=LOGGING_LEVEL,  # Capture ALL logs (INFO, DEBUG, ERROR)  # Set to DEBUG if you want to see debug logs of discord.http's request function
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # Ensure logs are printed to Replit console
    ]
)
logger = logging.getLogger(__name__)  # ✅ Use logger instead of print()


intents2 = discord.Intents.default()
intents2.messages = True
intents2.message_content = True
intents2.reactions = True
intents2.members = True
intents2.guilds = True
play2earn_bot = commands.Bot(command_prefix="!", intents=intents2)

invites = {}  # {guild.id: {code: uses}}
invite_user_map = {}  # {member_id: (used_code, inviter_id)}


@play2earn_bot.event
async def on_ready():
    global invites, invite_user_map

    # ✅ Initialize PostgreSQL (for this process)
    await init_pg()
    logger.info("✅ Connected to PostgreSQL in play2earn_bot process.")

    
    for guild in play2earn_bot.guilds:
        invite_list = await guild.invites()
        invites[guild.id] = {invite.code: invite.uses for invite in invite_list}

    invite_user_map = restore_invite_user_map()

    play2earn_bot.add_view(SupportView())

    #asyncio.create_task(update_minutes_pricepool_stats()) # commented because not actual total minutes but submited proof total minutes
                                                           # for now I will update the total minutes and price pool manually 
    asyncio.create_task(update_members_stats())
    asyncio.create_task(update_leaderboard_loop()) 

    logger.info("⏱️ Started automatic leaderboard updates every x seconds.")

    logger.info("✅Play2Earn Bot is ready!")


async def update_leaderboard_loop():
    await play2earn_bot.wait_until_ready()
    while not play2earn_bot.is_closed():
        try:
            await update_leaderboard()
        except Exception as e:
            logger.error(f"❌ leaderboard update failed: {e}")
        await asyncio.sleep(6)  # or whatever interval you want


async def update_leaderboard():
    def escape_discord_markdown(text: str) -> str:
        """Escapes Discord markdown characters to prevent formatting."""
        escape_chars = ['\\', '*', '_', '~', '`', '|', '>']
        for char in escape_chars:
            text = text.replace(char, f"\\{char}")
        return text


    leaderboard_raw = get_leaderboard_top_users(limit=99)

    # Filter out users with embedded tags
    leaderboard = [
        user for user in leaderboard_raw
        if "XOWNERX" not in user['name'] and "XCONTENTCREATORX" not in user['name']
    ]

    # Header lines
    lines = [
        " \# | Name |🎲 Gewinnchance |⏱ Spielzeit |🔗 Einladungen | ✅ Creator Code\n"
    ]

    # Row lines
    for i, user in enumerate(leaderboard, 1):
        raw_name = user['name'][:9]  if len(user['name']) > 10 else user['name']
        name = escape_discord_markdown(raw_name)
        lines.append(
            f"{i:<2} | {name:<10} | **{user['total_chance']:^5}** | {user['played_minutes']:^5} | {user['invites']:^3} | {user['creator_code']:^4}"
        )

    leaderboard_text = "\n".join(lines)


    leaderboard_channel = play2earn_bot.get_channel(LEADERBOARD_CHANNEL_ID)
    if leaderboard_channel is None:
        leaderboard_channel = await play2earn_bot.fetch_channel(LEADERBOARD_CHANNEL_ID)
        logger.debug("✅ Fetched leaderboard channel")

    try:
        leaderboard_msg = await leaderboard_channel.fetch_message(LEADERBOARD_MESSAGE_ID)
        await leaderboard_msg.edit(content=f"\n{leaderboard_text}\n")
        #logger.info("🔁 Leaderboard updated (code block style).")
    except discord.HTTPException as e:
        logger.warning(f"❌ Failed to update leaderboard: {e}")




async def update_minutes_pricepool_stats():
    await play2earn_bot.wait_until_ready()
    while not play2earn_bot.is_closed():
        try:
            guild = play2earn_bot.get_guild(GUILD_ID)
            if not guild:
                logger.warning("❌ Guild not found")
                return

            total_minutes = calculate_total_minutes_played()
            income_per_hour = 0.05 # 0.05$ map income per hour per 1 player
            pricepool_value = int(total_minutes / 60 * income_per_hour)
            print(total_minutes)

            if total_minutes:
                minutes_channel = guild.get_channel(MINUTES_PLAYED_ID)
                if minutes_channel:
                    desired_name_minutes = f"Minutes Played: {short_int(total_minutes)}"
                    if True: #minutes_channel.name != desired_name_minutes:
                        await minutes_channel.edit(name=desired_name_minutes)
                        logger.info(f"✅ Edited minutes channel name to: {desired_name_minutes}")


                pricepool_channel = guild.get_channel(PRICE_POOL_ID)
                if pricepool_channel:
                    desired_name_pricepool = f"💵│Price Pool: ${short_int(pricepool_value)}"
                    if True: #pricepool_channel.name != desired_name_pricepool:
                        await pricepool_channel.edit(name=desired_name_pricepool)
                        logger.info(f"✅ Edited pricepool channel name to: {desired_name_pricepool}")
        except Exception as e:
            logger.error(f"❌ Live update failed: {e}")
        await asyncio.sleep(305)  # ✅ Every 5 minutes because API per route limit is 2 requests per 10 minutes


def short_int(num: int):
    if num < 1000:
        return num
    if num < 1000000:
        return f"{num / 1000:.1f}K"
    if num < 1000000000:
        return f"{num / 1000000:.1f}M"
    if num < 1000000000000:
        return f"{num / 1000000000:.1f}B"
    

def calculate_total_minutes_played():
    total = 0
    for file in os.listdir("data"):
        if file.endswith(".json"):
            with open(os.path.join("data", file), "r", encoding="utf-8") as f:
                user_data = json.load(f)
                if user_data:
                    minutes = user_data["played_minutes"]
                    if minutes:
                        total += minutes
    return total




async def update_members_stats():
    await play2earn_bot.wait_until_ready()
    while not play2earn_bot.is_closed():
        try:
            guild = play2earn_bot.get_guild(GUILD_ID)
            member_channel = guild.get_channel(MEMBERS_STATS_ID)
            if member_channel:
                member_count = len(guild.members)
                await member_channel.edit(name=f"Members: {member_count}")
                logger.info(f"✅ Edited member channel name to: {member_count}")
        except Exception as e:
            logger.error(f"❌ member stats update failed: {e}")
        await asyncio.sleep(305)  # ✅ Every 5 minutes because API per route limit is 2 requests per 10 minutes



@play2earn_bot.command(name="creator")
async def creator(ctx):
    member = ctx.author
    guild = ctx.guild
    channel = ctx.channel

    # ✅ Check if it's a private thread
    if not isinstance(channel, discord.Thread) or channel.type != discord.ChannelType.private_thread:
        return

    # ✅ Check if the parent channel's name is "support"
    if channel.parent and "support" not in channel.parent.name.lower():
        return

    # ✅ Check if user has the "Content Creator" role
    content_creator_role = discord.utils.get(member.roles, name="Content Creator")
    if not content_creator_role:
        contentcreator = discord.utils.get(guild.roles, name="Content Creator")
        await ctx.send(f"❌ Du hast nicht die {contentcreator.mention} Rolle.")
        return

    # ✅ Load inviter data
    inviter_data = load_user_data(member.id)
    if not inviter_data:
        await ctx.send(f"❌ Fehler. Warte auf einen Mod {discord.utils.get(guild.roles, name='Mod').mention}")
        return

    invited_user_ids = inviter_data.get("invite", {}).get("invited_users", [])
    if not invited_user_ids:
        await ctx.send("ℹ️ Du hast noch keine erfolgreichen Einladungen.")
        return

    successful_invites = len(invited_user_ids)

    total_minutes = 0
    for user_id in invited_user_ids:
        user_data = load_user_data(user_id)
        if user_data:
            minutes = user_data.get("played_minutes", 0)
            if minutes:
                total_minutes += minutes

    
    earnings = round((total_minutes / 60) * 0.05, 2)  # 💵 0.05$/hour

    embed = discord.Embed(
        title="📊 Your Invite Stats",
        color=discord.Color.green()
    )
    embed.add_field(name=f"🔗 Erfolgreiche Einladungen: {str(successful_invites)}", value="", inline=False)
    embed.add_field(name=f"🕒 Gesamte Spielzeit durch Einladungen: {short_int(total_minutes)} Minuten", value="", inline=False)
    embed.add_field(name=f"💵 Deine Earnings: **${earnings}**",
                    value=f"Berechnung: ({total_minutes} mins ÷ 60) × $0.05 = **${earnings}**   basierend auf $0.05/hour", inline=False)
    embed.set_footer(text="Danke fürs Unterstüzen des Projektes! ❤️")

    await ctx.send(embed=embed)
    



@play2earn_bot.event
async def on_member_join(member):
    global invites

    role = discord.utils.get(member.guild.roles, name="Neu")
    if role:
        await member.add_roles(role)
        logger.debug(f"✅ Assigned Neu role to {member.display_name}")
    else:
        logger.warning(f"❌ Neu role not found in {member.guild.name}")

    guild = member.guild
    new_invites = await guild.invites()

    old_invites = invites[guild.id]
    used_invite = None

    for invite in new_invites:
        old_uses = old_invites.get(invite.code, 0)
        if invite.uses > old_uses:
            used_invite = invite
            break

    if used_invite:
        inviter_total_invites = save_invite_join_to_database(member, used_invite)

        # Store in memory
        used_code, inviter_id = used_invite.code, used_invite.inviter.id
        invite_user_map[member.id] = (used_code, inviter_id)

        # Update local invite cache
        invites[guild.id] = {invite.code: invite.uses for invite in new_invites}

        inviter_member = guild.get_member(inviter_id)
        if inviter_member is None:
            # Not cached, fetch from API
            inviter_member = await guild.fetch_member(inviter_id)

        owner_role = discord.utils.get(inviter_member.roles, name="Owner")

        if owner_role:
            invite_channel = play2earn_bot.get_channel(INVITE_CHANNEL_ID)
            await invite_channel.send(f"{member.mention} ist dem Server beigetreten.")
        else:
            invite_channel = play2earn_bot.get_channel(INVITE_CHANNEL_ID)
            
                
            content_creator_role = discord.utils.get(inviter_member.roles, name="Content Creator")
            if content_creator_role:
                # 🎥 Special message for content creators
                await invite_channel.send(
                    f"Der Content Creator {inviter_member.mention} invited {member.mention} und hat jetzt "
                    f"**{inviter_total_invites}** erfolgreiche Einladungen!"
                )
            else:
                await invite_channel.send(f"{used_invite.inviter.mention} invited {member.mention} "
                                          f"und hat jetzt {inviter_total_invites} Einladungen und somit **{inviter_total_invites*1}x** "
                                          f"mehr Gewinnchance für das Giveaway!")
                inviter_role = discord.utils.get(member.guild.roles, name="Inviter")
                if inviter_role:
                    inviter_member = guild.get_member(inviter_id)
                    if inviter_member is None:
                        # Not cached, fetch from API
                        inviter_member = await guild.fetch_member(inviter_member.author.id)
                    await inviter_member.add_roles(inviter_role)
                    logger.info(f"✅ Assigned Inviter role to {inviter_member.display_name}")




@play2earn_bot.event
async def on_member_remove(member):
    used_code, inviter_id = invite_user_map.get(member.id, (None, None))
    guild = member.guild
    if inviter_id:
        inviter_total_invites = save_invite_remove_to_database(member, inviter_id)
        invite_channel = play2earn_bot.get_channel(INVITE_CHANNEL_ID)
        
        inviter_member = guild.get_member(inviter_id)
        if inviter_member is None:
            # Not cached, fetch from API
            inviter_member = await guild.fetch_member(inviter_id)

        owner_role = discord.utils.get(inviter_member.roles, name="Owner")

        if owner_role:
            await invite_channel.send(f"{member.mention} hat den Server verlassen.")
        else:
            content_creator_role = discord.utils.get(inviter_member.roles, name="Content Creator")
            if content_creator_role:
                # 🎥 Special message for content creators
                await invite_channel.send(f"{member.mention} hat den Server verlassen. Der Content Creator {inviter_member.mention} hat jetzt "
                      f"**{inviter_total_invites}** erfolgreiche Einladungen.")
            else:
                await invite_channel.send(f"{member.mention} hat den Server verlassen. Der Inviter {inviter_member.mention} hat jetzt "
                                          f"{inviter_total_invites} Einladungen und somit **{inviter_total_invites*1}x** "
                                          "mehr Gewinnchance für das Giveaway!")
                
    
    invite_user_map.pop(member.id, None)


@play2earn_bot.event
async def on_invite_create(invite):
    invites.setdefault(invite.guild.id, {})[invite.code] = invite.uses
    logger.debug(f"✅ Invite created: {invite.code}")

@play2earn_bot.event
async def on_invite_delete(invite):
    invites.get(invite.guild.id, {}).pop(invite.code, None)
    logger.debug(f"✅ Invite deleted: {invite.code}")


class SupportView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🟩 Support", style=discord.ButtonStyle.success, custom_id="support_button")
    async def support_button(self, interaction: discord.Interaction, button: Button):
        user = interaction.user
        channel = interaction.channel
        guild = interaction.guild

        # Generate expected thread name
        expected_thread_name = f"Support-{user.name}"

        existing_thread = discord.utils.get(channel.threads, name=expected_thread_name)

        if existing_thread:
            await interaction.response.send_message(
                f"❗ Du hast schon einen Support Ticket: {existing_thread.mention}",
                ephemeral=True
            )
            return

        # Create a private thread under the original support channel
        thread = await channel.create_thread(
            name=expected_thread_name,
            type=discord.ChannelType.private_thread,
            invitable=False
        )

        await thread.add_user(user)

        await thread.send(f"👋 {user.mention} - {discord.utils.get(guild.roles, name='Mod').mention} \n" 
                           "Was ist dein Anliegen?")
        await interaction.response.send_message(f"✅ Dein Support Ticket wurde erstellt! {thread.mention}", ephemeral=True)











