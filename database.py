import psycopg2
import re
from config import config

def connect():
    conn = None
    try:
        params = config()
        print("Connecting to the postgreSQL database...")
        conn = psycopg2.connect(**params)
    except(Exception, psycopg2.DatabaseError) as error:
        print(error)

    return conn
   
def check_table(connection, table_name):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT to_regclass('public.{table_name}');")
        return cursor.fetchone()[0]

def initialize(connection):
    cursor = connection.cursor()
    cursor.execute("SET client_encoding TO 'UTF8';")

    if check_table(connection, "users") == None:
        cursor.execute("CREATE TABLE users (ID SERIAL PRIMARY KEY, discord VARCHAR(255) NOT NULL, osu_username VARCHAR(255) NOT NULL, team VARCHAR(255));")
        print("User table created")

    if check_table(connection, "matches") == None:
        cursor.execute("CREATE TABLE matches (ID SERIAL PRIMARY KEY, matchID VARCHAR(255) NOT NULL, stage VARCHAR(255) NOT NULL, raid_num INT NOT NULL, map_slot VARCHAR(255) NOT NULL, map_id VARCHAR(255) NOT NULL, team VARCHAR(255) NOT NULL, discord_id VARCHAR(255) NOT NULL, mp_link VARCHAR(255) NOT NULL, played BIT, last_update TIMESTAMP);")
        cursor.execute("ALTER TABLE matches ADD COLUMN mp_link VARCHAR(255);")
        cursor.execute("ALTER TABLE matches ADD COLUMN last_update TIMESTAMP DEFAULT now();")
        cursor.execute("ALTER TABLE matches ADD COLUMN p1_score VARCHAR(255);")
        cursor.execute("ALTER TABLE matches ADD COLUMN p2_score VARCHAR(255);")
        cursor.execute("ALTER TABLE matches ADD COLUMN p3_score VARCHAR(255);")
        cursor.execute("ALTER TABLE matches ADD COLUMN p4_score VARCHAR(255);")
        cursor.execute("ALTER TABLE matches ADD COLUMN p1_name VARCHAR(255);")
        cursor.execute("ALTER TABLE matches ADD COLUMN p2_name VARCHAR(255);")
        cursor.execute("ALTER TABLE matches ADD COLUMN p3_name VARCHAR(255);")
        cursor.execute("ALTER TABLE matches ADD COLUMN p4_name VARCHAR(255);")
        cursor.execute("ALTER TABLE matches ADD COLUMN map_num VARCHAR(255);")
        print("Match table created")

    if check_table(connection, "user_ids") == None:
        cursor.execute("CREATE TABLE user_ids (ID SERIAL PRIMARY KEY, osu_username VARCHAR(255) NOT NULL, user_id VARCHAR(255) NOT NULL);")
        print("ID table created")

    if check_table(connection, "mappools") == None:
        cursor.execute("CREATE TABLE mappools (ID SERIAL PRIMARY KEY, stage VARCHAR(255), slot VARCHAR(255), map_id VARCHAR(255));")
        print("Mappool table created")

    if check_table(connection, "teams") == None:
        cursor.execute("CREATE TABLE teams (ID SERIAL PRIMARY KEY, team_name VARCHAR(255), role_id VARCHAR(255), channel_id VARCHAR(255), team_avatar VARCHAR(255), team_color VARCHAR(255), raid_bonus FLOAT);")
        print("Team table created")

    connection.commit()

def insert_data(connection, data: dict, table: str):
    cursor = connection.cursor()

    if table == "users":
        cursor.execute(f"INSERT INTO users (discord, osu_username) VALUES ('{data['discord']}', '{data['osu_username']}');")

    if table == "user_ids":
        cursor.execute(f"INSERT INTO user_ids (osu_username, user_id) VALUES ('{data['osu_username']}', '{data['user_id']}');")
    
    if table == "matches":
        cursor.execute(f"INSERT INTO matches (matchID, stage, raid_num, map_slot, map_id, team, discord_id, played) VALUES ('{data['matchID']}', '{data['stage']}', '{data['raid_num']}', '{data['map_slot']}', '{data['map_id']}', '{data['team']}', '{data['discord_id']}', B'0');")
    
    if table == "mappools":
        cursor.execute(f"INSERT INTO mappools (stage, slot, map_id) VALUES ('{data['stage']}', '{data['slot']}', '{data['id']}');")

    if table == "teams":
        for key in data:
            cursor.execute(f"INSERT INTO teams (team_name, role_id, channel_id, team_avatar, team_color) VALUES ('{key}', '{data[key][0]}', '{data[key][1]}', '{data[key][2]}', '{data[key][3]}');")

    connection.commit()

def update_teams(connection, team: str, osu_username: str, discord: str):
    cursor = connection.cursor()
    cursor.execute(f"UPDATE users SET team='{team}' WHERE osu_username='{osu_username}' AND discord='{discord}';")

    connection.commit()

def update_discord(connection, before: str, after: str):
    cursor = connection.cursor()
    cursor.execute(f"UPDATE users SET discord='{after}' WHERE discord='{before}';")

    connection.commit()

def update_discord_manual(connection, discord: str, osu_username: str):
    cursor = connection.cursor()
    cursor.execute(f"UPDATE users SET discord='{discord}' WHERE osu_username='{osu_username}';")

    connection.commit()

def update_avatars(connection, avatar: str, discord: str):
    cursor = connection.cursor()
    cursor.execute(f"UPDATE users SET avatar='{avatar}' WHERE discord='{discord}';")

    connection.commit()

def get_mp_links(connection, team: str, stage: str):
    cursor = connection.cursor()
    cursor.execute(f"SELECT mp_link from matches WHERE team='{team}' AND stage='{stage}' AND map_slot='NM1';")

    return list(cursor)

def check_data(connection, data: str, table: str):
    cursor = connection.cursor()

    cursor.execute(f"SELECT * FROM {table};")
    for tournament in list(cursor):
        if data['osu_username'] in tournament:
            return True
    
    return False

def get_table(connection, table: str):
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM {table} ORDER BY ID ASC;")

    return list(cursor)

def get_table_time(connection):
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM matches ORDER BY last_update DESC;")

    return list(cursor)

def get_user(connection, osu_username: str):
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM users WHERE osu_username='{osu_username}';")

    return list(cursor)

def get_avatar(connection, osu_username: str):
    cursor = connection.cursor()
    cursor.execute(f"SELECT avatar FROM users WHERE osu_username='{osu_username}';")

    return list(cursor)

def get_team_members(connection, team: str):
    cursor = connection.cursor()
    cursor.execute(f"SELECT * from users WHERE team='{team}';")

    return list(cursor)

def get_unplayed_maps(connection, team: str, stage: str):
    cursor = connection.cursor()
    cursor.execute(f"SELECT map_slot from matches WHERE team='{team}' AND stage='{stage}' AND played=B'0';")

    return list(cursor)

def get_played_var(connection, team: str, stage: str, raid_num, map_slot: str):
    cursor = connection.cursor()
    cursor.execute(f"SELECT played FROM matches WHERE team='{team}' AND stage='{stage}' AND raid_num='{raid_num}' AND map_slot='{map_slot}';")

    return list(cursor)

def get_raid(connection, team: str, stage: str, raid_num):
    cursor = connection.cursor()
    cursor.execute(f"SELECT * from matches WHERE team='{team}' AND stage='{stage}' AND raid_num='{raid_num}' AND played=B'1' ORDER BY ID ASC;")

    return list(cursor)

def get_user_id(connection, osu_username: str):
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM user_ids WHERE osu_username='{osu_username}';")

    return list(cursor)

def get_role_id(connection, team: str):
    cursor = connection.cursor()
    cursor.execute(f"SELECT role_id FROM teams WHERE team_name='{team}';")

    return list(cursor)

def get_channel_id(connection, team: str):
    cursor = connection.cursor()
    cursor.execute(f"SELECT channel_id FROM teams WHERE team_name='{team}';")

    return list(cursor)

def get_team_avatar(connection, team: str):
    cursor = connection.cursor()
    cursor.execute(f"SELECT team_avatar FROM teams WHERE team_name='{team}';")

    return list(cursor)

def get_team_color(connection, team: str):
    cursor = connection.cursor()
    cursor.execute(f"SELECT team_color FROM teams WHERE team_name='{team}';")

    return list(cursor)

def get_raid_bonus(connection, team: str):
    cursor = connection.cursor()
    cursor.execute(f"SELECT raid_bonus FROM teams WHERE team_name='{team}';")

    return list(cursor)

def get_team(connection, role_id: str):
    cursor = connection.cursor()
    cursor.execute(f"SELECT team_name FROM teams WHERE role_id='{role_id}';")

    return list(cursor)

def get_all_teams(connection):
    cursor = connection.cursor()
    cursor.execute(f"SELECT team_name FROM teams;")

    return list(cursor)

def get_user_from_id(connection, id: str):
    cursor = connection.cursor()
    cursor.execute(f"SELECT osu_username FROM user_ids WHERE user_id = '{id}';")

    return list(cursor)

def cancel_match(connection, team: str, type: str, stage: str, raid_num: str):
    cursor = connection.cursor()
    cursor.execute("CREATE TABLE temp (ID SERIAL PRIMARY KEY, team VARCHAR(255), type VARCHAR(255), stage VARCHAR(255), raid_num VARCHAR(255));")
    cursor.execute(f"INSERT INTO temp (team, type, stage, raid_num) VALUES ('{team}', '{type}', '{stage}', '{raid_num}');")

    connection.commit()

def remove(connection, item: str, column: str, table: str):
    cursor = connection.cursor()
    cursor.execute(f"DELETE FROM {table} WHERE {column}='{item}';")

    connection.commit()

