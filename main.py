import discord, os, json
from discord.ext import commands
from discord.ui import Button, View
from replit import db

CATEGORY_ID = 1329571928482250835  # category "SupportAmar" in order to only take supportAmar request into account
WELCOME_CHANNEL_ID = 1329571928951754823

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix="!", intents=intents)

print(db, db.keys())
db_data = {key: db[key] for key in db.keys()}
print(json.dumps(db_data))

class VerifyView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify",
                       style=discord.ButtonStyle.green,
                       custom_id="verify_button")
    async def verify(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        user = interaction.user
        channel = guild.get_channel(WELCOME_CHANNEL_ID)

        # check if the user already has an open thread
        existing_thread = discord.utils.get(
            channel.threads, name=f"{user.name.lower()}-verification")
        if existing_thread:
            await interaction.response.send_message(
                f"❌ You already have an open ticket: {existing_thread.mention}",
                ephemeral=True)
            return

        # create a private thread for the user
        thread = await channel.create_thread(
            name=f"{user.name.lower()}-verification",
            type=discord.ChannelType.private_thread,
            invitable=False  # Ensures only invited users can join
        )
        # Add the user to the thread
        await thread.add_user(user)

        # Send a message in the thread
        await thread.send(
            f"Hello {user.mention}! Please type your Epic Games ID below. Once entered, I'll ask you to confirm it!"
        )

        # Respond to the user in the main channel
        await interaction.response.send_message(
            f"✅ Your private ticket has been created: {thread.mention}",
            ephemeral=True)


class ConfirmationView(View):

    def __init__(self, thread, user):
        super().__init__(timeout=None)
        self.thread = thread
        self.user = user

    @discord.ui.button(label="Yes",
                       style=discord.ButtonStyle.green,
                       custom_id="confirm_yes")
    async def confirm_yes(self, interaction: discord.Interaction,
                          button: Button):
        if interaction.user != self.user:
            await interaction.response.send_message(
                "You are not authorized to respond here.", ephemeral=True)
            return

        await interaction.response.send_message(
            "✅ Thank you! Your Epic Games ID has been confirmed and saved.",
            ephemeral=True)
        db[f"epic_{self.user.id}"] = interaction.message.content.split(
            "Is ")[1].split(" your Epic Games ID?")[0]
        print(db)
        await self.thread.send("✅ Your Epic Games ID has been saved.")

    @discord.ui.button(label="No, enter again",
                       style=discord.ButtonStyle.red,
                       custom_id="confirm_no")
    async def confirm_no(self, interaction: discord.Interaction,
                         button: Button):
        if interaction.user != self.user:
            await interaction.response.send_message(
                "You are not authorized to respond here.", ephemeral=True)
            return

        await interaction.response.send_message(
            "❌ Please enter your Epic Games ID again below.", ephemeral=True)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    channel = bot.get_channel(WELCOME_CHANNEL_ID)

    if channel:
        # Clear all messages in the channel
        await channel.purge(limit=100)
        embed = discord.Embed(
            title="SupportAmar Ticketsystem",
            description=
            "Hier ....  \n Drücke auf Verifizieren, um zu verifieren, dass du Amar supportest!",
            color=discord.Color.blue())
        view = VerifyView()

        await channel.send(embed=embed, view=view)


@bot.event
async def on_message(message):
    # Ignore bot messages
    if message.author.bot:
        return

    # Check if the message is in a private thread
    if isinstance(
            message.channel, discord.Thread
    ) and message.channel.type == discord.ChannelType.private_thread:
        # check if message is in the supportAmar category
        if message.channel.parent:
            parent_channel = message.channel.parent
            if parent_channel.category and parent_channel.category.id != CATEGORY_ID:
                print("rip", parent_channel.category.id)
                return
        user = message.author
        thread = message.channel
        epic_id = message.content.strip()

        # Prompt the user to confirm their Epic Games ID
        await thread.send(f"Is `{epic_id}` your Epic Games ID?",
                          view=ConfirmationView(thread, user))


bot.run(os.getenv('TOKEN'))
