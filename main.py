import discord
import os
import sheets
from dotenv import load_dotenv
import asyncio
from threading import Thread
import subprocess
import random
import database
from datetime import datetime, timezone
import requests

from discord.ext.commands import Bot
from discord import app_commands
from discord.ext import tasks

load_dotenv()
BOT_PREFIX = "-"
intents = discord.Intents.all()
intents.members = True
TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
API_KEY = os.environ.get('OSU_API_KEY')
client = Bot(command_prefix=BOT_PREFIX, intents=intents)
node_processes = []
observers = []
cancellations = []
ready_json = {}
sent = False
connection = database.connect()
database.initialize(connection)

def run_cancellation():
    cancellations.append(subprocess.Popen(["node", "./osubot/cancel.js"]))
    print('Starting cancellation...\n')
    output = cancellations[-1]

def run_node_server():
    node_processes.append(subprocess.Popen(["node", "./osubot/app.js"]))
    print('Starting server...\n')
    output = node_processes[-1]

def run_observer():
    observers.append(["python3", "./fileobserver.py"])
    print('Starting observer...\n')
    output = subprocess.Popen(observers[-1]) 
    
def get_value(data, value, val_type, return_val):
    for entry in data:
        if entry[val_type] == value:
            return entry[return_val]
        
def username_to_member(guild: discord.Guild, name: str):
    for member in guild.members:
        if member.name == name:
            return member
    return None

def get_map_data(mapid: str):
    url = "https://osu.ppy.sh/api/get_beatmaps?k=" + API_KEY + "&b=" + mapid
    response = requests.get(url)

    return response.json()[0]

def get_beatmaptitle(mapid: str):
    url = "https://osu.ppy.sh/api/get_beatmaps?k=" + API_KEY + "&b=" + mapid
    response = requests.get(url)
    artist = response.json()[0]['artist']
    difficulty = response.json()[0]['version']
    title = artist + ' - ' + response.json()[0]['title'] + ' ['+difficulty+']'

    return title

def get_userid(player: str):
    url = 'https://osu.ppy.sh/api/get_user'
    u = player
    m = 0
    type = 'string'
    url = url + '?u=' + u + '&m=' + str(m) + '&type=' + type + '&k=' + API_KEY
    response = requests.get(url)
    return response.json()[0]['user_id']

def add_match(interaction: discord.Interaction, type: str):
    user_json = database.get_table(connection, "users")
    match_json = database.get_table(connection, "matches")
    mappool = database.get_table(connection, "mappools")[::-1]
    stage = mappool[0][1]
    pool_index = 0
    raid_num = 1
    maps = []
    matchID = ""
    discord_id = interaction.user.name
    team = get_value(user_json, discord_id, 1, 3)

    for map in mappool:
        if mappool[pool_index][1] == stage:
            maps.append({
                "slot": mappool[pool_index][2],
                "id": mappool[pool_index][3]
            })
        pool_index += 1

    random.shuffle(maps)
    match_json.reverse()

    for match in match_json:
        if team in match and stage in match:
            raid_num = int(match[3])+1 
            break
    
    if raid_num == 3:
        unplayed_map_slots = []
        unplayed_maps = []
        unplayed_dicts = []
        for slot in database.get_unplayed_maps(connection, team, stage):
            if slot[0] in unplayed_map_slots:
                unplayed_maps.append(slot[0])
            unplayed_map_slots.append(slot[0])
        
        print(unplayed_maps)
        print(unplayed_map_slots)
        
        for map in maps:
            if map['slot'] in unplayed_maps:
                unplayed_dicts.append(map)
                maps.remove(map)
        
        maps.extend(unplayed_dicts)
        maps.reverse()

        print(maps)

    if type.lower() == "`normal`":
        matchID = "Normal"
        
    elif type.lower() == "`elite`":
        matchID = "Elite"
    
    if raid_num <= 3:
        for map in maps:
            database.insert_data(connection, {
                "matchID": matchID,
                "stage": stage,
                "raid_num": raid_num,
                "map_slot": map['slot'],
                "map_id": map['id'],
                "team": team,
                "discord_id": discord_id
            },"matches")
    else:
        return False

    return True

class Start_Menu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Start", style=discord.ButtonStyle.green)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True

        await interaction.response.edit_message(content=interaction.message.content, view=self)
        await interaction.message.delete(delay=60)
        
        try:
            await asyncio.sleep(1)
            
            stage = interaction.message.content.split()
            if add_match(interaction, stage[5]):
                ready_json.clear()
                server = Thread(target=run_node_server)
                await interaction.followup.send(f"Raid confirmed! Invites will be sent to all team members soon. If you did not get it or lost the invite, DM {os.environ.get('USERNAME')} `.invite` on osu! for another link.")
                server.start()
            else:
                await interaction.followup.send("You have hit the max amt of raids for this week.")
    
        except FileNotFoundError:
            await interaction.followup.send("Slow down! You are spamming the button too much.", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
    
        try:
            ready_json.clear()
            await interaction.message.delete()
            await interaction.response.defer()
            await asyncio.sleep(1)
            await interaction.followup.send("Match setup has been cancelled.")
        except FileNotFoundError:
            await interaction.response.send_message("Slow down! You are spamming the button too much.", ephemeral=True)
    

class Menu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Ready", style=discord.ButtonStyle.blurple)
    async def ready(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = str(interaction.user)
        user_json = database.get_table(connection, "users")
        type = interaction.message.content.split()[6]
        team = interaction.message.content.split()[0][3:-1]
        team = database.get_team(connection, team)[0][0]
        user_team = get_value(user_json, str(interaction.user), 1, 3)
        reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣']
        
        if user not in ready_json:
            if user_team != team:
                await interaction.response.send_message(f"{interaction.user.mention}, You are not a part of {team}.")
            else:
                if (len(ready_json) == 1):
                    button.disabled = True
                    await interaction.message.clear_reactions()
                    await interaction.message.add_reaction(reactions[len(ready_json)])
                    await interaction.response.edit_message(content=interaction.message.content, view=self)
                    view = Start_Menu()
                    await interaction.followup.send(f"Press Start to commence the {type} raid! Please open osu! beforehand so that you can receive the invite. This will also time out in one minute if not pressed.", view=view)
                else:
                    ready_json[user] = team
                    await interaction.message.clear_reactions()
                    await interaction.message.add_reaction(reactions[len(ready_json)-1])
                    await interaction.response.send_message(f"You have readied up!", ephemeral=True)
        else:
            await interaction.message.remove_reaction(reactions[len(ready_json)-1], interaction.message.author)
            ready_json.pop(user, None)
            await interaction.response.send_message(f"You have unreadied.", ephemeral=True)
        
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        ready_json.clear()

        try:
            await interaction.message.delete()
            await interaction.response.defer()
            await asyncio.sleep(1)
            await interaction.followup.send("Match setup has been cancelled.")
        except FileNotFoundError:
            await interaction.response.send_message("Slow down! You are spamming the button too much.", ephemeral=True)

@client.tree.command(name="bake", description="Admin only command")
async def bake_all(interaction: discord.InteractionMessage):
    if interaction.user.guild_permissions.administrator:
        user_json = database.get_table(connection, "users")
        player_sheet = sheets.get_values(os.environ.get("PLAYER_TAB"), os.environ.get("GOOGLE_SHEET_ID"), 'A2:H')
        
        for player in player_sheet:
            if len(player) > 1:
                discord = player[3].lower()
                osu_username = player[2]
            else:
                break

            if get_value(user_json, discord, 1, 2) != None:
                await interaction.response.send_message(
                    f"All players are up to date.", ephemeral=True)
                return
            else:
                database.insert_data(connection,{
                    "discord": discord,
                    "osu_username": osu_username
                }, "users")

        await interaction.response.send_message(
            f"Successfully linked all players!",
        ephemeral=True)
    else:
        await interaction.response.send_message(f"You are not allowed to use this command.")

@client.tree.command(name="halfbake", description="Admin only command")
async def halfbake(interaction: discord.InteractionMessage):
    if interaction.user.guild_permissions.administrator:
        user_json = database.get_table(connection, "users")
        player_sheet = sheets.get_values(os.environ.get("PLAYER_TAB"), os.environ.get("GOOGLE_SHEET_ID"), 'A2:H')
        
        for player in player_sheet:
            if len(player) > 1:
                user_id = player[1]
                osu_username = player[2]
            else:
                break

            if get_value(user_json, user_id, 1, 2) != None:
                await interaction.response.send_message(
                    f"All players are up to date.", ephemeral=True)
                return
            else:
                database.insert_data(connection,{
                    "user_id": user_id,
                    "osu_username": osu_username
                }, "user_ids")

        await interaction.response.send_message(
            f"Successfully linked all players!",
        ephemeral=True)
    else:
        await interaction.response.send_message(f"You are not allowed to use this command.")

@client.tree.command(name="add_avatars", description="Admin only command")
async def add_avatars(interaction: discord.InteractionMessage):
    if interaction.user.guild_permissions.administrator:
        player_sheet = sheets.get_values(os.environ.get("PLAYER_TAB"), os.environ.get("GOOGLE_SHEET_ID"), 'A2:I')
        
        for player in player_sheet:
            if len(player) > 1:
                avatar = player[5]
                discord = player[3]
            else:
                break

            database.update_avatars(connection, avatar, discord)

        await interaction.response.send_message(
            f"Successfully linked all players!",
        ephemeral=True)
    else:
        await interaction.response.send_message(f"You are not allowed to use this command.")

@client.tree.command(name="play_raid", description="Start a raid (normal or elite)")
@app_commands.choices(type=[
    discord.app_commands.Choice(name='Normal', value='normal'),
    discord.app_commands.Choice(name='Elite', value='elite')
])
async def play_raid(interaction: discord.Interaction, type: app_commands.Choice[str]):
    no_role = True
    ready_json.clear()
    for role in interaction.user.roles:
        if len(node_processes) == 3:
            await interaction.response.send_message("The maximum amount of raids is currently ongoing, please wait for one to finish.")
        else:
            for team in database.get_all_teams(connection):
                if role.name in team[0]:
                    no_role = False
                    view = Menu()
                    user_json = database.get_table(connection, "users")

                    try:
                        team = get_value(user_json, str(interaction.user), 1, 3)
                        role_id = database.get_role_id(connection, team)[0][0]
                        await interaction.response.send_message(f"<@&{role_id}> Press ready to begin your `{type.value}` raid. At least two people from the team must be ready to start the raid. If not enough players are ready by one minute this message will time out.", view=view, allowed_mentions=discord.AllowedMentions(everyone=True), delete_after=60)
                    except KeyError:
                        await interaction.response.send_message("Your discord is outdated, ask an admin to update it.")
            
    if no_role:
        await interaction.response.send_message(f"You are not allowed to use this command.")

@client.tree.command(name="update_discord", description="Updates a user's discord to the db")
async def update_discord(interaction: discord.Interaction, new_discord: str, osu_username: str):
    if interaction.user.guild_permissions.administrator:
        try:
            database.update_discord_manual(connection, new_discord, osu_username)
            await interaction.response.send_message(f"Successfully linked `{new_discord}` to `{osu_username}`")
        except TypeError:
            await interaction.response.send_message("Could not find user.")
    else:
        await interaction.response.send_message(f"You are not allowed to use this command.")

@client.tree.command(name="unbake", description="Admin only command")
async def unbake(interaction: discord.Interaction, discord: str, osu_username: str):
    if interaction.user.guild_permissions.administrator:
        try:
            database.remove(connection, osu_username, "osu_username", "users")
            await interaction.response.send_message(f"Successfully unlinked `{discord}` to `{osu_username}`")
        except TypeError:
            await interaction.response.send_message("Could not find user.")
    else:
        await interaction.response.send_message(f"You are not allowed to use this command.")

@client.tree.command(name="upload_mappool", description="Uploads mappool to the database")
@app_commands.choices(type=[
    discord.app_commands.Choice(name='RO32', value='ROUND OF 32'),
    discord.app_commands.Choice(name='RO16', value='ROUND OF 16'),
    discord.app_commands.Choice(name='QF', value='QUARTERFINALS'),
    discord.app_commands.Choice(name='SF', value='SEMIFINALS'),
    discord.app_commands.Choice(name='F', value='FINALS'),
    discord.app_commands.Choice(name='GF', value='GRAND FINALS'),
])
async def upload_mappool(interaction: discord.Interaction, type: app_commands.Choice[str]):
    if interaction.user.guild_permissions.administrator:
        try:
            pool_sheet = sheets.get_values(os.environ.get("POOL_TAB"), os.environ.get("POOL_SHEET_ID"), 'A1:O')
            pool_sheet = [[i for i in item if i != ''] for item in pool_sheet]
            pool_sheet = [item for item in pool_sheet if item != []]
            pool_index = 0

            for pool in pool_sheet:
                if type.value in pool:
                    break
                else:
                    pool_index += 1
            pool_index += 2

            while pool_sheet[pool_index][0] != "TB":
                database.insert_data(connection, {
                    "stage": type.name,
                    "slot": pool_sheet[pool_index][0],
                    "id": pool_sheet[pool_index][-1]
                }, "mappools")
                pool_index += 1
            await interaction.response.send_message(f"Successfully uploaded the `{type.name}` mappool!")
        except:
            await interaction.response.send_message("Could not upload mappool currently.")
            
    else:
        await interaction.response.send_message(f"You are not allowed to use this command.")

@client.tree.command(name="raid_mp_links", description="Posts team raid mps for a given stage")
@app_commands.choices(type=[
    discord.app_commands.Choice(name='QF', value='QUARTERFINALS'),
    discord.app_commands.Choice(name='SF', value='SEMIFINALS'),
    discord.app_commands.Choice(name='F', value='FINALS'),
    discord.app_commands.Choice(name='GF', value='GRAND FINALS'),
])
async def raid_mp_links(interaction: discord.Interaction, type: app_commands.Choice[str]):
    no_role = True
    for role in interaction.user.roles:
        for team in database.get_all_teams(connection):
            if role.name in team:
                no_role = False
                user_json = database.get_table(connection, "users")

                try:
                    team = get_value(user_json, str(interaction.user), 1, 3)
                    mp_string = f"{type.name} raids for {team}:\n"
                    mp_links = database.get_mp_links(connection, team, type.name)

                    for link in mp_links:
                        if link[0] != None:
                            mp_string += link[0]+"\n"
                    
                    await interaction.response.send_message(mp_string)
                    
                except TypeError:
                    await interaction.response.send_message("No mp links found.")
            
    if no_role:
        await interaction.response.send_message(f"You are not allowed to use this command.")

@client.tree.command(name="cancel_raid", description="Admin only command")
@app_commands.choices(type=[
    discord.app_commands.Choice(name='Normal', value='normal'),
    discord.app_commands.Choice(name='Elite', value='elite')
])
async def cancel_raid(interaction: discord.Interaction, team: str, type: app_commands.Choice[str], stage: str, raid_num: str):
    if interaction.user.guild_permissions.administrator:
        database.cancel_match()
        server = Thread(target=run_cancellation)
        server.start()
    else:
        await interaction.response.send_message(f"You are not allowed to use this command.")

@tasks.loop(seconds=1.0)
async def logger():
    channel = client.get_channel(1330072245321859094)
    logged = False

    if os.path.exists("./templog.txt") and not logged:
        file = open("templog.txt", "r")
        templine = file.readline()
        logged = True
        file.close()
        await channel.send(templine)
    if os.path.exists("./templog.txt") and logged:
        os.remove("./templog.txt")
        logged = False
                
@tasks.loop(seconds=1.0)
async def process_check():
    #channel = client.get_channel(1265881389786730611) public bot channel
    channel = client.get_channel(1255892723790250118)
    status = discord.Game('Currently serving ' + str(len(node_processes)) + ' raids!')
    await client.change_presence(activity=status)
    if node_processes:
        for process in node_processes:
            poll = process.poll()
            if poll is not None:
                print("Server has been closed")
                node_processes.remove(process)
                #channel.send("The previous lobby has finished")

@tasks.loop(seconds=1.0)
async def match_check():
    now = datetime.now()
    utc_now = datetime.now(timezone.utc)
    matches = database.get_table_time(connection)
    if (now - matches[0][10]).total_seconds() < 1 and database.get_played_var(connection, matches[0][6], matches[0][2], matches[0][3], matches[0][4])[0][0] == '1':
        channel = client.get_channel(1330072245321859094)
        map_num = matches[0][19]
        total_score = 0
        field_count = 0
        scores = [{
            'score': matches[0][11],
            'name': matches[0][15]
            }, {
            'score': matches[0][12],
            'name': matches[0][16]
            }, {
            'score': matches[0][13],
            'name': matches[0][17]
            }, {
            'score': matches[0][14],
            'name': matches[0][18]
        }]
        scores_int = []

        embed = discord.Embed(
            title=f"{matches[0][6]} have finished map {map_num}: {get_beatmaptitle(matches[0][5])}",
            colour=discord.Color.from_str(database.get_team_color(connection, matches[0][6])[0][0]),
            timestamp=utc_now
        )
        
        embed.set_author(name=f"{matches[0][6]} | {matches[0][2]} | Raid #{matches[0][3]} | {matches[0][1]}", icon_url=database.get_team_avatar(connection, matches[0][6])[0][0])

        for score in scores:
            if score['name'] != None:
                embed.add_field(name=f"{score['name']}", value=f"{score['score']}", inline=True)
                field_count += 1
                total_score += int(score['score'])
                scores_int.append(int(score['score']))

                if field_count % 2 == 0:
                    embed.add_field(name='\u200b', value='\u200b', inline=True)

        max_score = max(scores_int)

        for score in scores:
            if str(max_score) in score.values():
                max_user = score['name']
                break
        
        max_user_id = get_userid(max_user)
        max_user = database.get_user_from_id(connection, max_user_id)[0][0]

        embed.add_field(name='\u200b', value=f"**Total score:** {total_score}", inline=False)
        embed.add_field(name='\u200b', value=f"[Match history]({matches[0][9]})", inline=True)
        embed.set_image(url='https://assets.ppy.sh/beatmaps/' + get_map_data(matches[0][5])[
        'beatmapset_id'] + '/covers/cover.jpg')
        embed.set_thumbnail(url=database.get_avatar(connection, max_user)[0][0])
        embed.set_footer(text='\u200b', icon_url=database.get_team_avatar(connection, matches[0][6])[0][0])
        
        if map_num == '10' and matches[0][1] == "Elite" or map_num == '5' and matches[0][1] == "Normal":
            field_count = 0
            total_raid_score = 0
            team_channel = client.get_channel(int(database.get_channel_id(connection, matches[0][6])[0][0]))
            raid = database.get_raid(connection, matches[0][6], matches[0][2], matches[0][3])
            
            result_embed = discord.Embed(
                title=f"{matches[0][6]} have completed {matches[0][2]} {matches[0][1]} Raid #{matches[0][3]}!",
                colour=discord.Color.from_str(database.get_team_color(connection, matches[0][6])[0][0]),
                timestamp=utc_now
            )

            result_embed.set_author(name=f"{matches[0][6]} | {matches[0][2]} | Raid #{matches[0][3]} | {matches[0][1]}", icon_url=database.get_team_avatar(connection, matches[0][6])[0][0])
            result_embed.set_thumbnail(url=database.get_team_avatar(connection, matches[0][6])[0][0])
            result_embed.set_footer(text='\u200b', icon_url=database.get_team_avatar(connection, matches[0][6])[0][0])

            for map in raid:
                player_str = ""
                
                for i in range(15, 19):
                    if map[i] != None:
                        player_str += f"\n▸ **{map[i]}**: {map[i-4]}"
                        total_raid_score += int(map[i-4])

                result_embed.add_field(name=f"Map {map[19]}:", value=f"[**{get_beatmaptitle(map[5])}**](https://osu.ppy.sh/b/{map[5]}){player_str}", inline=False)
            
            result_embed.add_field(name='\u200b', value=f"**Raid score:** {total_raid_score}\n**Raid bonus:** {database.get_raid_bonus(connection, matches[0][6])[0][0]}%\n[Match history]({matches[0][9]})", inline=False)
            await team_channel.send(embed=result_embed)
            
        await channel.send(embed=embed)


@tasks.loop(seconds=1.0)
async def assign_teams():
    guild = client.get_guild(1292748316622196757)
    team_sheet = sheets.get_values(os.environ.get("TEAM_TAB"), os.environ.get("GOOGLE_SHEET_ID"), 'A2:X')
    user_json = database.get_table(connection, "users")

    for team in team_sheet:
        players = [team[4], team[9], team[14], team[19]]
        for player in players:
            if player != None:
                if get_value(user_json, player, 2, 1) != None:
                    if get_value(user_json, player, 2, 3) != team[1]:
                        team_name = team[1]
                        discord_id = get_value(user_json, player, 2, 1)
                        
                        database.update_teams(connection, team_name, player, discord_id)
                        member = username_to_member(guild, discord_id)
                        role_id = database.get_role_id(connection, team_name)[0][0]
                        if member:
                            await member.edit(roles=[discord.utils.get(guild.roles, id=1293586741583679551), discord.utils.get(guild.roles, id=role_id)])

@client.event
async def on_user_update(before,after):
    if before.name != after.name:
        database.update_discord(connection, before.name, after.name)

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

    try:
        synced = await client.tree.sync()
        print(f"synced {len(synced)} command(s)")
    except Exception as e:
        print(e)
    observer = Thread(target=run_observer)
    observer.start()
    logger.start()
    process_check.start()
    match_check.start()

    status = discord.Game('Currently serving ' + str(len(node_processes)) + ' raids!')
    await client.change_presence(activity=status)

client.run(TOKEN)