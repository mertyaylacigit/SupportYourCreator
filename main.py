import discord, os, json
from discord.ext import commands
from discord.ui import Modal, TextInput, Button, View
from config import TOKEN, WELCOME_CHANNEL_ID, CATEGORY_ID
from database_handler import save_epic_name_to_database, save_image_to_database

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
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
        # Check if the message has an attachment (image/video)
        if message.attachments:
            print(f"Message:{message}")
            print(f"Attachments:{message.attachments}")
            allowed_file_types = ["image", "video"]

            # Check if the attachment is an image or video
            for attachment in message.attachments:
                for file_type in allowed_file_types:
                    if file_type in attachment.content_type:
                        if file_type == "image":
                            print(f" It is a {attachment.content_type} file.")
                            image_url = attachment.url
                            save_image_to_database(message.author.id, image_url)
                            return
                            
                        if file_type == "video":
                            print(f" It is a {attachment.content_type} file. TODO: video handling")
                            return

        # If the message is not an image or video, delete it
        #await message.delete()
        await message.channel.send(f"❌ {message.author.mention} schreibe hier bitte nichts, damit der Verlauf clean bleibt (:")


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    channel = bot.get_channel(WELCOME_CHANNEL_ID)

    if channel:
        # Purge all threads in the channel (only for development)
        for thread in channel.threads:
            try:
                await thread.delete()
                print(f"🗑️ Thread gelöscht: {thread.name}")
            except Exception as e:
                print(f"❌ Konnte den Thread {thread.name} nicht löschen: {e}")

        await channel.purge()

        embed = discord.Embed(
            title="SupportAmar Ticketsystem",
            description="Hier kannst du verifizieren, dass du Amar supportest. \nDrücke auf **Verifizieren**, um zu beginnen!",
            color=discord.Color.blue()
        )
        view = Welcome2VerifyView()
        await channel.send(embed=embed, view=view)


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

        thread = await channel.create_thread(
            name=f"{user.name.lower()}-verifizierung",
            type=discord.ChannelType.private_thread,
            invitable=False
        )
        await thread.add_user(user)
        embed = discord.Embed(
            title="Gib deine Epic Games ID ein",
            description="Drücke auf den Button unten, um deine Epic Games ID einzugeben.",
            color=discord.Color.blue()
        )
        view = Verify2EnterIDView(thread, user)

        await thread.send(embed=embed, view=view)

        await interaction.response.send_message(f"✅ Dein privates Ticket wurde erstellt: {thread.mention}", ephemeral=True)


class Verify2EnterIDView(BaseView):
    def __init__(self, thread, user):
        super().__init__(timeout=None)
        self.thread = thread
        self.user = user

    @discord.ui.button(label="Epic Games ID eingeben", style=discord.ButtonStyle.blurple, custom_id="enter_epic_id")
    async def enter_epic_id(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.user:
            await interaction.response.send_message("Du bist nicht berechtigt, dies zu tun.", ephemeral=True)
            return

        await interaction.response.send_modal(EpicIDModal(self.thread, self.user, self))


class EnterID2ConfirmView(BaseView):
    def __init__(self, thread, user):
        super().__init__(timeout=None)
        self.thread = thread
        self.user = user

    @discord.ui.button(label="Ja", style=discord.ButtonStyle.green, custom_id="confirm_yes")
    async def confirm_yes(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.user:
            await interaction.response.send_message("Du bist nicht berechtigt, dies zu tun.", ephemeral=True)
            return
        # Extract the embed description
        embed = interaction.message.embeds[0]  # Get the first embed
        if embed and embed.description:
            # Extract the Epic Games ID from the description
            epic_name = embed.description.split("`")[1]  # Extract the text between backticks
            discord_id = f"userID_{self.user.id}"
            save_epic_name_to_database(discord_id, epic_name)
            
        await interaction.response.send_message("✅ Danke! Deine Epic Games ID wurde bestätigt und gespeichert.", ephemeral=True)
        #await self.thread.send("✅ Deine Epic Games ID wurde gespeichert.")

        # Disable the buttons after clicking
        await self.disable_buttons(interaction)

        # next step: proof code registration
        embed = discord.Embed(
            title="Creator Code Amar eingetragen?",
            description=(
                "Bitte lade ein Beweisbild hoch, das zeigt, dass du den Creator Code benutzt hast:\n\n🔹 **Das Bild sollte Folgendes zeigen:**\n"
                "1️⃣ Dein **Epic Games Konto**.\n"
                "2️⃣ Den Artikel im **Fortnite Shop**, bei dem der Creator Code sichtbar ist.\n\n"
                "🔸 **So lädst du das Bild hoch:**\n"
                "- Drücke unten auf das **+** Symbol oder ziehe das Bild in den Thread.\n"
                "- Stelle sicher, dass das Bild klar und lesbar ist.\n\n"
                "**Beachte:** Nur Bilder, die über Discords Upload-Funktion gesendet werden, werden akzeptiert."
                "➡️ **Das Bild sollte ungefähr so aussehen:**"
            ),
            color=discord.Color.blue()
        )
        embed.set_image(url="https://cdn.discordapp.com/attachments/894683986868203551/1337204328628486186/image.png?ex=67a69814&is=67a54694&hm=e2e5a97814f60b2d9d5b62d2bfb34be0350f14185ce9982f43ce6ff18c55bfcb&")
        embed.set_footer(text="Vielen Dank für deinen Support! ❤️")
        await self.thread.send(embed=embed)

    @discord.ui.button(label="Nein, erneut eingeben", style=discord.ButtonStyle.red, custom_id="confirm_no")
    async def confirm_no(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.user:
            await interaction.response.send_message("Du bist nicht berechtigt, dies zu tun.", ephemeral=True)
            return

        await interaction.response.send_modal(EpicIDModal(self.thread, self.user, self))


class EpicIDModal(Modal):
    def __init__(self, thread, user, parent_view):
        super().__init__(title="Gib deine Epic Games ID ein")
        self.thread = thread
        self.user = user
        self.parent_view = parent_view
        self.text = TextInput(
            label="Gib deine Epic Games ID ein",
            placeholder="z.B. EpicGamer123",
            required=True
        )
        self.add_item(self.text)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        print(self.text, "aa", self.text.value)

        embed = discord.Embed(
            title="Bestätige deine Eingabe",
            description=f"Ist `{self.text.value}` deine Epic Games ID?",
            color=discord.Color.blue()
        )
        view = EnterID2ConfirmView(self.thread, self.user)

        await self.thread.send(embed=embed, view=view)
        # disable views button only when user submitted. Otherwise buttons would be disabled after user cancels form and is stuck
        await self.parent_view.disable_buttons(interaction)




    


bot.run(TOKEN)
