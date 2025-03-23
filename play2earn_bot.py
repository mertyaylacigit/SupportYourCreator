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
from config import TOKEN_play2earn, LOGGING_LEVEL, INVITE_CHANNEL_ID
from db_handler import save_invite_join_to_database, save_invite_remove_to_database, restore_invite_user_map, init_pg

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

    logger.info("✅Play2Earn Bot is ready!")



@play2earn_bot.event
async def on_member_join(member):
    global invites

    role = discord.utils.get(member.guild.roles, name="New")
    if role:
        await member.add_roles(role)
        logger.info(f"✅ Assigned New role to {member.display_name}")
    else:
        logger.warning(f"❌ New role not found in {member.guild.name}")
        
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

        if used_invite.code == "7gJcKcg954" or used_invite.code == "UaUqP8E7AM": # ignore main invite link # UaUqP8E7AM is from SYC dev
            invite_channel = play2earn_bot.get_channel(INVITE_CHANNEL_ID)
            await invite_channel.send(f"{member.mention} joined the server.")
        else:
            invite_channel = play2earn_bot.get_channel(INVITE_CHANNEL_ID)
            await invite_channel.send(f"{used_invite.inviter.mention} invited {member.mention} "
                                      f"and has now {inviter_total_invites} invites, thus **{inviter_total_invites*1}x** "
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
    if inviter_id:
        inviter_total_invites = save_invite_remove_to_database(member, inviter_id)

        if used_code == "7gJcKcg954" or used_code == "UaUqP8E7AM": # ignore main invite link # UaUqP8E7AM is from SYC dev
            invite_channel = play2earn_bot.get_channel(INVITE_CHANNEL_ID)
            await invite_channel.send(f"{member.mention} left the server.")
        else:
            invite_channel = play2earn_bot.get_channel(INVITE_CHANNEL_ID)
            inviter = play2earn_bot.get_user(inviter_id)
            await invite_channel.send(f"{member.mention} left the channel and the inviter {inviter.mention} has "
                                      f"now {inviter_total_invites} invites, thus **{inviter_total_invites*1}x** "
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


