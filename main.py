import os
import discord
from discord import app_commands

TOKEN = os.environ.get("DISCORD_TOKEN")

TEAM_ROLE_IDS = [
    1507947463028506678,
    1507947465939226795,
    1507947468229181530,
    1507947475967803412
]

CAPTAIN_ROLE_ID = 1187722813386276885

def is_authorized(member):
    if member.guild_permissions.administrator:
        return True
    return any(role.id == CAPTAIN_ROLE_ID for role in member.roles)

class Client(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

client = Client()

def get_team_role(member):
    for role in member.roles:
        if role.id in TEAM_ROLE_IDS:
            return role
    return None

async def move_players(players, new_role):
    for player in players:
        old_role = get_team_role(player)
        if old_role:
            await player.remove_roles(old_role)
        await player.add_roles(new_role)

class ConfirmTrade(discord.ui.View):
    def __init__(self, team_a_players, team_b_players, team_a_role, team_b_role):
        super().__init__(timeout=None)
        self.team_a_players = team_a_players
        self.team_b_players = team_b_players
        self.team_a_role = team_a_role
        self.team_b_role = team_b_role

    @discord.ui.button(label="Confirm Trade", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Only admins can confirm trades.", ephemeral=True)

        await interaction.response.defer()

        await move_players(self.team_a_players, self.team_b_role)
        await move_players(self.team_b_players, self.team_a_role)

        team_a_names = "\n".join([f"• {p.mention}" for p in self.team_a_players])
        team_b_names = "\n".join([f"• {p.mention}" for p in self.team_b_players])

        for item in self.children:
            item.disabled = True

        await interaction.message.edit(
            content=
            f"✅ **TRADE CONFIRMED**\n\n"
            f"**{self.team_b_role.name} receive:**\n"
            f"{team_a_names}\n\n"
            f"**{self.team_a_role.name} receive:**\n"
            f"{team_b_names}\n\n"
            f"Confirmed by {interaction.user.mention}",
            view=self
        )

@client.tree.command(name="sign", description="Sign an unsigned player to your team")
@app_commands.describe(player="The player to sign")
async def sign(interaction: discord.Interaction, player: discord.Member):
    if not is_authorized(interaction.user):
        return await interaction.response.send_message("Only captains and admins can use this command.", ephemeral=True)

    if get_team_role(player):
        return await interaction.response.send_message(f"{player.mention} is already on a team. Use `/trade` to move them.", ephemeral=True)

    signer_team = get_team_role(interaction.user)
    if not signer_team and not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("You are not on a team, so you cannot sign players.", ephemeral=True)

    if not signer_team:
        return await interaction.response.send_message("Admins must use `/freetransfer` to assign players. You need to be on a team to use `/sign`.", ephemeral=True)

    await interaction.response.defer()
    await player.add_roles(signer_team)

    await interaction.followup.send(
        f"✅ **PLAYER SIGNED**\n\n"
        f"{player.mention} has been signed to **{signer_team.name}**.\n\n"
        f"Signed by {interaction.user.mention}"
    )

@client.tree.command(name="roster", description="List all players on each team")
async def roster(interaction: discord.Interaction):
    if not is_authorized(interaction.user):
        return await interaction.response.send_message("Only captains and admins can use this command.", ephemeral=True)

    await interaction.response.defer()

    guild = interaction.guild
    lines = []

    for role_id in TEAM_ROLE_IDS:
        role = guild.get_role(role_id)
        if not role:
            continue
        members = [m for m in guild.members if role in m.roles]
        if members:
            names = "\n".join([f"• {m.mention}" for m in members])
            lines.append(f"**{role.name}** ({len(members)} players)\n{names}")
        else:
            lines.append(f"**{role.name}** — no players")

    if not lines:
        return await interaction.followup.send("No team roles found.", ephemeral=True)

    await interaction.followup.send("📋 **TEAM ROSTERS**\n\n" + "\n\n".join(lines))


@client.tree.command(name="trade", description="Create a trade request between teams")
async def trade(
    interaction: discord.Interaction,
    team_a_player_1: discord.Member,
    team_b_player_1: discord.Member,
    team_a_player_2: discord.Member = None,
    team_a_player_3: discord.Member = None,
    team_a_player_4: discord.Member = None,
    team_a_player_5: discord.Member = None,
    team_b_player_2: discord.Member = None,
    team_b_player_3: discord.Member = None,
    team_b_player_4: discord.Member = None,
    team_b_player_5: discord.Member = None
):
    if not is_authorized(interaction.user):
        return await interaction.response.send_message("Only captains and admins can use this command.", ephemeral=True)

    await interaction.response.defer()

    team_a_players = [p for p in [team_a_player_1, team_a_player_2, team_a_player_3, team_a_player_4, team_a_player_5] if p]
    team_b_players = [p for p in [team_b_player_1, team_b_player_2, team_b_player_3, team_b_player_4, team_b_player_5] if p]

    team_a_role = get_team_role(team_a_player_1)
    team_b_role = get_team_role(team_b_player_1)

    if not team_a_role:
        return await interaction.followup.send(f"{team_a_player_1.mention} has no team role.", ephemeral=True)

    if not team_b_role:
        return await interaction.followup.send(f"{team_b_player_1.mention} has no team role.", ephemeral=True)

    if team_a_role.id == team_b_role.id:
        return await interaction.followup.send("Both players are already on the same team.", ephemeral=True)

    for player in team_a_players + team_b_players:
        if not get_team_role(player):
            return await interaction.followup.send(f"{player.mention} has no team role.", ephemeral=True)

    team_a_names = "\n".join([f"• {p.mention}" for p in team_a_players])
    team_b_names = "\n".join([f"• {p.mention}" for p in team_b_players])

    view = ConfirmTrade(team_a_players, team_b_players, team_a_role, team_b_role)

    await interaction.followup.send(
        f"🔄 **TRADE PENDING**\n\n"
        f"**{team_b_role.name} receive:**\n"
        f"{team_a_names}\n\n"
        f"**{team_a_role.name} receive:**\n"
        f"{team_b_names}\n\n"
        f"Waiting for an admin to confirm.",
        view=view
    )

client.run(TOKEN, reconnect=True)
