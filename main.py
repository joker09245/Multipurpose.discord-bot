import os
import discord
import json
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
from collections import defaultdict
import datetime

# --- Load configuration from .env ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID'))

# --- Define bot intents ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.guilds = True

# --- Initialize the bot ---
bot = commands.Bot(command_prefix='!', intents=intents)

# --- Global state variables ---
afk_users = {}
PREMIUM_SERVERS_FILE = 'premium_servers.json'

# --- Anti-nuke thresholds and state ---
WHITELISTED_USERS = [OWNER_ID]
ACTION_THRESHOLD = 5
TIME_WINDOW_SECONDS = 10
nuke_actions = defaultdict(lambda: {'bans': 0, 'kicks': 0, 'channels': 0, 'roles': 0, 'timestamp': datetime.datetime.now()})

# --- Watermark (Branding) ---
WATERMARK_TEXT = "Developed by Joker Development"

# --- Helper functions for premium servers ---
def load_premium_servers():
    if os.path.exists(PREMIUM_SERVERS_FILE):
        with open(PREMIUM_SERVERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_premium_servers(data):
    with open(PREMIUM_SERVERS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

premium_servers = load_premium_servers()

# --- Helper function for watermarked embeds ---
def create_watermarked_embed(title, description=None, color=None):
    """Creates a standard embed with the developer watermark in the footer."""
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=WATERMARK_TEXT)
    return embed

# --- Anti-nuke handler function ---
async def handle_nuke_action(member, action_type, context):
    """Handles an anti-nuke violation."""
    if member.id in WHITELISTED_USERS or member.id == member.guild.owner_id:
        return

    now = datetime.datetime.now()
    user_data = nuke_actions[member.id]

    if (now - user_data['timestamp']).total_seconds() > TIME_WINDOW_SECONDS:
        user_data['bans'] = 0
        user_data['kicks'] = 0
        user_data['channels'] = 0
        user_data['roles'] = 0
        user_data['timestamp'] = now

    if action_type in user_data:
        user_data[action_type] += 1
    
    if user_data.get(action_type, 0) >= ACTION_THRESHOLD:
        try:
            await member.ban(reason=f"Automated anti-nuke ban for excessive {action_type}.")
            
            for role in member.roles:
                if role.permissions.administrator or role.permissions.manage_channels or role.permissions.manage_roles:
                    await member.remove_roles(role, reason="Anti-nuke: Stripping dangerous permissions.")
            
            owner = member.guild.owner
            if owner:
                await owner.send(
                    f"**[Anti-Nuke Triggered]**\n"
                    f"User **{member}** (`{member.id}`) was automatically banned for mass-{action_type}."
                )

            nuke_actions.pop(member.id, None)

        except discord.Forbidden:
            owner = member.guild.owner
            if owner:
                await owner.send(
                    f"**[Anti-Nuke Failed]**\n"
                    f"Attempted to ban malicious user **{member}** (`{member.id}`) for mass-{action_type}, "
                    f"but the bot lacks the necessary permissions. Please review my permissions immediately."
                )
        except Exception as e:
            owner = member.guild.owner
            if owner:
                await owner.send(
                    f"**[Anti-Nuke Error]**\n"
                    f"An unexpected error occurred while handling a security incident involving user **{member}**: `{e}`"
                )

# --- Discord Events for Anti-Nuke ---
@bot.event
async def on_member_ban(guild, user):
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
        if entry.target == user:
            await handle_nuke_action(entry.user, 'bans', entry)

@bot.event
async def on_member_remove(member):
    async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
        if entry.target == member:
            await handle_nuke_action(entry.user, 'kicks', entry)

@bot.event
async def on_guild_channel_create(channel):
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
        if entry.target == channel:
            await handle_nuke_action(entry.user, 'channels', entry)

@bot.event
async def on_guild_channel_delete(channel):
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        if entry.target == channel:
            await handle_nuke_action(entry.user, 'channels', entry)

@bot.event
async def on_guild_role_create(role):
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
        if entry.target == role:
            await handle_nuke_action(entry.user, 'roles', entry)

@bot.event
async def on_guild_role_delete(role):
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        if entry.target == role:
            await handle_nuke_action(entry.user, 'roles', entry)

# --- Bot Events ---
@bot.event
async def on_ready():
    print(f'{bot.user.name} is now online!')
    print('--------------------')

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # AFK mention handling
    if any(user.id in afk_users and user != message.author for user in message.mentions):
        for member in message.mentions:
            if member.id in afk_users:
                reason = afk_users[member.id]
                await message.channel.send(f"{member.mention} is AFK: {reason}\n*{WATERMARK_TEXT}*", suppress_embeds=True)
    
    # Check if the author is AFK
    if message.author.id in afk_users:
        del afk_users[message.author.id]
        await message.channel.send(f"Welcome back, {message.author.mention}! Your AFK status has been removed.\n*{WATERMARK_TEXT}*", suppress_embeds=True)

    # Owner-only no-prefix commands
    if message.author.id == OWNER_ID:
        if message.content.lower() == 'sync':
            await bot.tree.sync()
            await message.channel.send(f"Slash commands synchronized globally.\n*{WATERMARK_TEXT}*", suppress_embeds=True)
            return

    await bot.process_commands(message)

# --- Moderation Commands ---
@bot.command(name='kick', help='Kicks a specified member from the server.')
@commands.has_permissions(kick_members=True)
@commands.bot_has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    if member == ctx.author:
        return await ctx.send(f"You can't kick yourself!\n*{WATERMARK_TEXT}*", suppress_embeds=True)
    if ctx.author.top_role.position <= member.top_role.position:
        return await ctx.send(f"You cannot kick this member because their role is higher or equal to yours.\n*{WATERMARK_TEXT}*", suppress_embeds=True)
    
    await member.kick(reason=reason)
    await ctx.send(f'Kicked {member.mention}. Reason: {reason or "No reason provided."}\n*{WATERMARK_TEXT}*', suppress_embeds=True)

@bot.command(name='ban', help='Bans a specified member from the server.')
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    if member == ctx.author:
        return await ctx.send(f"You can't ban yourself!\n*{WATERMARK_TEXT}*", suppress_embeds=True)
    if ctx.author.top_role.position <= member.top_role.position:
        return await ctx.send(f"You cannot ban this member because their role is higher or equal to yours.\n*{WATERMARK_TEXT}*", suppress_embeds=True)
    
    await member.ban(reason=reason)
    await ctx.send(f'Banned {member.mention}. Reason: {reason or "No reason provided."}\n*{WATERMARK_TEXT}*', suppress_embeds=True)

@bot.command(name='unban', help='Unbans a member by their username and tag.')
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def unban(ctx, *, member_name_and_discriminator):
    banned_users = [entry async for entry in ctx.guild.bans()]
    name, discriminator = member_name_and_discriminator.split('#')

    for ban_entry in banned_users:
        user = ban_entry.user
        if (user.name, user.discriminator) == (name, discriminator):
            await ctx.guild.unban(user)
            return await ctx.send(f'Unbanned {user.mention}.\n*{WATERMARK_TEXT}*', suppress_embeds=True)
    await ctx.send(f'Could not find a banned user named "{member_name_and_discriminator}".\n*{WATERMARK_TEXT}*', suppress_embeds=True)

@bot.command(name='role', help='Adds or removes a role from a member.')
@commands.has_permissions(manage_roles=True)
@commands.bot_has_permissions(manage_roles=True)
async def manage_role(ctx, member: discord.Member, role: discord.Role):
    if ctx.author.top_role.position <= role.position and ctx.author.id != ctx.guild.owner_id:
        return await ctx.send(f"You cannot manage this role as it's higher or equal to your own.\n*{WATERMARK_TEXT}*", suppress_embeds=True)
    
    if role.position >= ctx.guild.me.top_role.position:
        return await ctx.send(f"I cannot manage this role because it is higher or equal to my own top role.\n*{WATERMARK_TEXT}*", suppress_embeds=True)

    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"Removed the role '{role.name}' from {member.mention}.\n*{WATERMARK_TEXT}*", suppress_embeds=True)
    else:
        await member.add_roles(role)
        await ctx.send(f"Added the role '{role.name}' to {member.mention}.\n*{WATERMARK_TEXT}*", suppress_embeds=True)

# --- Fun Commands ---
@bot.command(name='fakenitro', help='Pranks a user with a fake Nitro gift message.')
async def fakenitro(ctx, user: discord.Member):
    embed = create_watermarked_embed(
        title="🎁 A Wild Gift Appeared!",
        description=f"**{user.mention}**, your friend **{ctx.author.mention}** has sent you **1 month of Discord Nitro!**\n\nClick the button below to accept your gift now!",
        color=0x7289DA
    )
    embed.set_thumbnail(url="https://i.imgur.com/y4L6e0t.png")
    embed.set_footer(text=f"{WATERMARK_TEXT} | A gift from Discord. Claim within 48 hours.") # Combined footer

    view = discord.ui.View()
    button = discord.ui.Button(label="Accept Gift", style=discord.ButtonStyle.green, emoji="🎁")

    async def button_callback(interaction: discord.Interaction):
        if interaction.user != user:
            return await interaction.response.send_message(
                "This gift wasn't for you! Sneaky, sneaky...", ephemeral=True
            )
        
        await interaction.response.send_message(
            f"Aw, shucks! Sorry {user.mention}, that was a prank by {ctx.author.mention}! 😜\n\nBetter luck next time!", 
            ephemeral=True
        )

    button.callback = button_callback
    view.add_item(button)
    
    await ctx.send(embed=embed, view=view)

@bot.command(name='afk', help='Sets your status as AFK (Away From Keyboard).')
async def afk(ctx, *, reason="No reason provided."):
    afk_users[ctx.author.id] = reason
    await ctx.send(f"{ctx.author.mention} is now AFK: {reason}\n*{WATERMARK_TEXT}*", suppress_embeds=True)

# --- Premium Server System ---
@commands.is_owner()
@bot.group(name='premium', invoke_without_command=True)
async def premium(ctx):
    await ctx.send(f"Invalid premium subcommand. Use `!premium activate` or `!premium deactivate`.\n*{WATERMARK_TEXT}*", suppress_embeds=True)

@commands.is_owner()
@premium.command(name='activate', help='(Owner Only) Activates premium status for a server.')
async def premium_activate(ctx, server_id: int):
    try:
        guild = bot.get_guild(server_id)
        if not guild:
            return await ctx.send(f"Server with ID `{server_id}` not found.\n*{WATERMARK_TEXT}*", suppress_embeds=True)
        
        premium_servers[str(server_id)] = True
        save_premium_servers(premium_servers)
        await ctx.send(f"Activated premium for server **{guild.name}** (`{server_id}`).\n*{WATERMARK_TEXT}*", suppress_embeds=True)
    except Exception as e:
        await ctx.send(f"An error occurred: {e}\n*{WATERMARK_TEXT}*", suppress_embeds=True)

@commands.is_owner()
@premium.command(name='deactivate', help='(Owner Only) Deactivates premium status for a server.')
async def premium_deactivate(ctx, server_id: int):
    if str(server_id) in premium_servers:
        premium_servers.pop(str(server_id))
        save_premium_servers(premium_servers)
        await ctx.send(f"Deactivated premium for server with ID `{server_id}`.\n*{WATERMARK_TEXT}*", suppress_embeds=True)
    else:
        await ctx.send(f"Server with ID `{server_id}` is not a premium server.\n*{WATERMARK_TEXT}*", suppress_embeds=True)

# --- Ticket Panel Setup (Premium Feature) ---
class TicketButton(discord.ui.View):
    def __init__(self, bot_instance, category_id, log_channel_id):
        super().__init__(timeout=None)
        self.bot = bot_instance
        self.category_id = category_id
        self.log_channel_id = log_channel_id

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.green, emoji="🎟️")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=self.category_id)
        log_channel = self.bot.get_channel(self.log_channel_id)

        ticket_channel = await category.create_text_channel(
            f"ticket-{interaction.user.name}",
            topic=f"Ticket for {interaction.user.name} ({interaction.user.id})"
        )
        
        await ticket_channel.set_permissions(interaction.guild.default_role, read_messages=False)
        await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)

        await ticket_channel.send(
            f"Hello {interaction.user.mention}! A staff member will be with you shortly.\n*{WATERMARK_TEXT}*", suppress_embeds=True
        )
        
        if log_channel:
            await log_channel.send(f"A new ticket was opened by {interaction.user.mention} in {ticket_channel.mention}.\n*{WATERMARK_TEXT}*", suppress_embeds=True)

        await interaction.response.send_message(
            f"Your ticket has been created! Please go to {ticket_channel.mention}.\n*{WATERMARK_TEXT}*", 
            ephemeral=True
        )

@bot.command(name='ticketsetup', help='(Premium Only) Sets up a ticket panel.')
@commands.has_permissions(administrator=True)
async def ticket_setup(ctx, category: discord.CategoryChannel, log_channel: discord.TextChannel):
    if str(ctx.guild.id) not in premium_servers:
        return await ctx.send(f"This is a premium-only command. Please activate premium for this server.\n*{WATERMARK_TEXT}*", suppress_embeds=True)

    embed = create_watermarked_embed(
        title="Need Support?",
        description="Click the button below to open a support ticket.",
        color=discord.Color.blue()
    )
    view = TicketButton(bot, category.id, log_channel.id)
    await ctx.send(embed=embed, view=view)

# --- Error Handling ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"You don't have the required permissions to use this command.\n*{WATERMARK_TEXT}*", suppress_embeds=True)
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(f"I don't have the required permissions to perform this action.\n*{WATERMARK_TEXT}*", suppress_embeds=True)
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send(f"Could not find the specified member.\n*{WATERMARK_TEXT}*", suppress_embeds=True)
    elif isinstance(error, commands.RoleNotFound):
        await ctx.send(f"Could not find the specified role.\n*{WATERMARK_TEXT}*", suppress_embeds=True)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required arguments. Usage: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`\n*{WATERMARK_TEXT}*", suppress_embeds=True)
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.NotOwner):
        await ctx.send(f"This command is for the bot owner only.\n*{WATERMARK_TEXT}*", suppress_embeds=True)
    else:
        print(f'An error occurred: {error}')
        await ctx.send(f"An unknown error occurred while running that command.\n*{WATERMARK_TEXT}*", suppress_embeds=True)

# --- Run the bot ---
bot.run(TOKEN)
  
