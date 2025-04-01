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
from config import LOGGING_LEVEL, INVITE_CHANNEL_ID, MEMBERS_STATS_ID, MINUTES_PLAYED_ID,  PRICE_POOL_ID, GUILD_ID
from db_handler import load_user_data, save_invite_join_to_database, save_invite_remove_to_database, restore_invite_user_map, init_pg

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

    logger.info("✅Play2Earn Bot is ready!")



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
                if user_data and "points_assigned" in user_data:
                    minutes = user_data["points_assigned"]
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
        await ctx.send(f"❌ You don't have the {contentcreator.mention} role.")
        return

    # ✅ Load inviter data
    inviter_data = load_user_data(member.id)
    if not inviter_data:
        await ctx.send("❌ Error occured. Wait for a Mod")
        return

    invited_user_ids = inviter_data.get("invite", {}).get("invited_users", [])
    if not invited_user_ids:
        await ctx.send("ℹ️ You haven't invited any users yet.")
        return

    successful_invites = len(invited_user_ids)

    total_minutes = 0
    for user_id in invited_user_ids:
        user_data = load_user_data(user_id)
        if user_data:
            minutes = user_data.get("points_assigned", 0)
            if minutes:
                total_minutes += minutes

    
    earnings = round((total_minutes / 60) * 0.05, 2)  # 💵 0.05$/hour

    embed = discord.Embed(
        title="📊 Your Invite Stats",
        color=discord.Color.green()
    )
    embed.add_field(name=f"🔗 Successful Invites: {str(successful_invites)}", value="", inline=False)
    embed.add_field(name=f"🕒 Total Minutes Played by Your Invites: {short_int(total_minutes)} minutes", value="", inline=False)
    embed.add_field(name=f"💵 Your Earnings: **${earnings}**",
                    value=f"Calculation: ({total_minutes} mins ÷ 60) × $0.05 = **${earnings}**   based on $0.05/hour", inline=False)
    embed.set_footer(text="Thank you for supporting the project! ❤️")

    await ctx.send(embed=embed)
    



@play2earn_bot.event
async def on_member_join(member):
    global invites
    
    role = discord.utils.get(member.guild.roles, name="Bronze")
    if role:
        await member.add_roles(role)
        logger.info(f"✅ Assigned Bronze role to {member.display_name}")
    else:
        logger.warning(f"❌ Bronze role not found in {member.guild.name}")

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
            await invite_channel.send(f"{member.mention} joined the server.")
        else:
            invite_channel = play2earn_bot.get_channel(INVITE_CHANNEL_ID)
            
                
            content_creator_role = discord.utils.get(inviter_member.roles, name="Content Creator")
            if content_creator_role:
                # 🎥 Special message for content creators
                await invite_channel.send(
                    f"The Content Creator {inviter_member.mention} invited {member.mention} and now has "
                    f"**{inviter_total_invites}** successful invites!"
                )
            else:
                await invite_channel.send(f"{used_invite.inviter.mention} invited {member.mention} "
                                          f"and now has {inviter_total_invites} invites, thus **{inviter_total_invites*1}x** "
                                          f"more chance to win the giveaway!")
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
            await invite_channel.send(f"{member.mention} left the server.")
        else:
            content_creator_role = discord.utils.get(inviter_member.roles, name="Content Creator")
            if content_creator_role:
                # 🎥 Special message for content creators
                await invite_channel.send(f"{member.mention} left the channel and the Content Creator {inviter_member.mention} now has "
                      f"**{inviter_total_invites}** successful invites.")
            else:
                await invite_channel.send(f"{member.mention} left the channel and the inviter {inviter_member.mention} now has "
                                          f"{inviter_total_invites} invites, thus **{inviter_total_invites*1}x** "
                                          "more chance to win the giveaway!")
                
    
    invite_user_map.pop(member.id, None)


@play2earn_bot.event
async def on_invite_create(invite):
    invites.setdefault(invite.guild.id, {})[invite.code] = invite.uses
    logger.info(f"✅ Invite created: {invite.code}")

@play2earn_bot.event
async def on_invite_delete(invite):
    invites.get(invite.guild.id, {}).pop(invite.code, None)
    logger.info(f"✅ Invite deleted: {invite.code}")


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
                f"❗ You already have an open Support-Thread: {existing_thread.mention}",
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
                           "What is your concern?")
        await interaction.response.send_message(f"✅ Your support ticket has been created! {thread.mention}", ephemeral=True)

