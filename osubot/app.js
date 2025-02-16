const Banchojs = require("bancho.js");
const nodesu = require('nodesu');
const { google } = require("googleapis");
const fs = require('fs');

const path = require('path')
require('dotenv').config({ path: path.resolve(__dirname, './.env') })

const serviceAccountKeyFile = `${process.env.SERVICE_ACCT_FILE}`;
const sheetId = `${process.env.GOOGLE_SHEET_ID}`;

const config = require('./config.json');
const api = new nodesu.Client(config.apiKey);

var pg = require('pg');
var conString = `${process.env.CONSTRING}`;

var pgClient = new pg.Client(conString);
pgClient.connect();
console.log("Connected to PostgreSQL");

async function getMatch() {
  matchID = pgClient.query(`SELECT * FROM matches ORDER BY ID DESC LIMIT 1;`);

  return matchID;
}

async function getCurrentBonus(team) {
  currentBonus = pgClient.query(`SELECT raid_bonus FROM teams WHERE team_name = '${team}'`);

  return currentBonus;
}

async function getMaps(matchID, stage, raidNum, team) {
  matches = pgClient.query(`SELECT * FROM matches WHERE matchID = '${matchID}' AND stage = '${stage}' AND raid_num = '${raidNum}' AND team = '${team}';`);

  return matches;
}

async function updatePlayedMap(map, raidNum, stage, team) {
  await pgClient.query(`UPDATE matches SET played = B'1' WHERE map_slot = '${map}' AND stage = '${stage}' AND raid_num = '${raidNum}' AND team = '${team}';`);
  await pgClient.query(`UPDATE matches SET last_update=now() WHERE map_slot = '${map}' AND stage = '${stage}' AND raid_num = '${raidNum}' AND team = '${team}';`);
}

async function updateMpLink(mpLink, raidNum, stage, team) {
  await pgClient.query(`UPDATE matches SET mp_link = '${mpLink}' WHERE stage = '${stage}' AND raid_num = '${raidNum}' AND team = '${team}';`);
}

async function updateDBScores(map, raidNum, stage, team, score, name, num, player) {
  await pgClient.query(`UPDATE matches SET p${player}_score = '${score}' WHERE stage = '${stage}' AND raid_num = '${raidNum}' AND team = '${team}' AND map_slot = '${map}';`);
  await pgClient.query(`UPDATE matches SET p${player}_name = '${name}' WHERE stage = '${stage}' AND raid_num = '${raidNum}' AND team = '${team}' AND map_slot = '${map}';`);
  await pgClient.query(`UPDATE matches SET map_num = '${num}' WHERE stage = '${stage}' AND raid_num = '${raidNum}' AND team = '${team}' AND map_slot = '${map}';`);
}

async function updateRaidBonus(team, type, currentBonus) {
  let bonus = 1.0;
  if (type === "Elite") {
    bonus = 1.5;
  }

  bonus = currentBonus + bonus;
  await pgClient.query(`UPDATE teams SET raid_bonus = '${bonus}' WHERE team_name = '${team}';`)
}

async function joinIds(team) {
  ids = pgClient.query(`SELECT u.ID, u.discord, u.osu_username, u.team, uid.user_id FROM users u JOIN user_ids uid ON u.osu_username = uid.osu_username WHERE team = '${team}';`);

  return ids;
}

getMatch().then((value) => {
  getMaps(value['rows'][0]['matchid'], value['rows'][0]['stage'], value['rows'][0]['raid_num'], value['rows'][0]['team']).then((value2) => {
    team = value2['rows'][0]['team'];
    stage = value2['rows'][0]['stage'];
    matchID = value2['rows'][0]['matchid'];
    raidNum = value2['rows'][0]['raid_num'];
    mapOrder = [];
    maxMaps = 5;

    if (matchID === "Elite") {
      maxMaps = 10;
    }

    for (map of value2['rows']) {
      mapOrder.push([map['map_slot'], map['map_id']]);
    }
    startOsuBot(team, mapOrder, stage, matchID, raidNum, maxMaps);
  });
});

let scoreIndex = 0;
let rowIndex = 0;
let firstIndex = 0;
let mapIndex = 0;
let mapsPlayed = 0;
let mapsCleared = 0;
let player = 1;
let cellIncrement = 5;
let validMods = 0;
let delay = 15000;
let data = [[]];
let timeout = false;
let firstScore = true;
let playerInTeam = false;

const client = new Banchojs.BanchoClient(config);

const prefix = ".";

async function _getGoogleSheetClient() {
  const auth = new google.auth.GoogleAuth({
    keyFile: serviceAccountKeyFile,
    scopes: ["https://www.googleapis.com/auth/spreadsheets"],
  });
  const authClient = await auth.getClient();
  return google.sheets({
    version: "v4",
    auth: authClient,
  });
}

async function _readGoogleSheet(googleSheetClient, sheetId, tabName, range) {
  const res = await googleSheetClient.spreadsheets.values.get({
    spreadsheetId: sheetId,
    range: `${tabName}!${range}`,
  });

  return res.data.values;
}


async function _writeGoogleSheet(
  googleSheetClient,
  sheetId,
  tabName,
  range,
  data,
) {
  await googleSheetClient.spreadsheets.values.append({
    spreadsheetId: sheetId,
    range: `${tabName}!${range}`,
    valueInputOption: "USER_ENTERED",
    insertDataOption: "OVERWRITE",
    resource: {
      majorDimension: "ROWS",
      values: data,
    },
  });
}


function log(data) {
  fs.appendFile("./osubot/log.txt", data, (err) => {
    if (err) throw err;
  });
}


async function updateScores(googleSheetClient, sheetId, tabName, range, data) {
  await googleSheetClient.spreadsheets.values.update({
    spreadsheetId: sheetId,
    range: `${tabName}!${range}`,
    valueInputOption: "USER_ENTERED",
    resource: {
      majorDimension: "ROWS",
      values: data,
    },
  });
}

async function updateData() {
  let column = "BC";
  let range = `B3:${column}`;

  const googleSheetClient = await _getGoogleSheetClient();
  const sheet = await _readGoogleSheet(
    googleSheetClient,
    sheetId,
    "rawraiddata",
    range,
  );

  if (sheet != undefined) {
    for (let i = 0; i < sheet.length; i++) {
      rowIndex++;
    }
  }

  updateScores(
    googleSheetClient,
    sheetId,
    "rawraiddata",
    `B${+rowIndex + 3}:${column}${+rowIndex + 3}`,
    data,
  );
}


async function startOsuBot(team, mapOrder, stage, matchID, raidNum, maxMaps) {
  try {
    await client.connect();
    setTimeout(log, 1000, "--------------------------------------------------------\n");
    setTimeout(log, 3000, "-# osu!bot Connected...\n");
    
    channel = await client.createLobby(
      `CRTOA: Raid #${raidNum}: (${stage} / ${matchID} / ${team})`,
      true
    );
  } catch (err) {
    console.error(err);
    setTimeout(log, 3000, "Failed to create lobby\n");
    process.exit(1);
  }

  lobby = channel.lobby;

  const mpLink = `https://osu.ppy.sh/mp/${lobby.id}`;
  const password = Math.random().toString(36).substring(8);
  await lobby.setPassword(password);
  setTimeout(log, 5000, "-# Lobby created!\n");
  setTimeout(log, 7000, `Name: ${lobby.name}, password: ${password}\n`);
  setTimeout(log, 9000, `Multiplayer link: <${mpLink}>\n`);
  updateMpLink(mpLink, raidNum, stage, team);

  data[0][0] = stage;
  data[0][1] = team;
  data[0][2] = raidNum;
  data[0][3] = matchID;
  
  scoreIndex = 5;

  lobby.setSettings(
    Banchojs.BanchoLobbyTeamModes.HeadToHead,
    Banchojs.BanchoLobbyWinConditions.ScoreV2,
    4,
  );
  setBeatmap(mapOrder[mapsPlayed][0], mapOrder[mapsPlayed][1]);

  joinIds(team).then((value) => {
    for (player of value['rows']) {
      setTimeout(log, delay, `Inviting player: ${player['osu_username']}\n`);
      lobby.invitePlayer(`#${player['user_id']}`);
      delay += +5000;
    }
  });

  delay = 15000;
  
  createListeners(matchID, raidNum, stage, team, maxMaps);
}

async function setBeatmap(slot, id) {
  getMapData(id).then((value) => {
    setTimeout(log, 13000, `Selecting map ${+mapsPlayed + 1}: ${value[0].artist} - ${value[0].title} [${value[0].version}]\n`);
    channel.sendMessage(`Selecting map ${+mapsPlayed + 1}: ${value[0].artist} - ${value[0].title} [${value[0].version}]`);
  });
  
  let mod = slot.slice(0, 2);
  if (mod.includes("NM")) {
    mod = "";
  } if(mod.includes("FM")) {
    mod = "freemod";
  }
  mod = mod + " NF";
  lobby.setMap(id);
  lobby.setMods(mod, false);
}

async function compareScore() {
  const scoreJson = lobby.scores;
  let totalScore = 0;

  for (score of scoreJson) {
    totalScore += +score.score;
  }

  if (totalScore < 50000) {
    return false;
  } else {
    return true;
  }
}

async function usernameToID(username) {
  return await api.user.get(username);
}

async function idsToUsername(ids) {
  let user;
  for (id of ids) {
    user = await api.user.get(id[0]);
    id[0] = user['username'];
  }

  return ids;
}

async function getMapData(id) {
  map = await api.beatmaps.getByBeatmapId(id);

  return map;
}

async function getScoreData() {
  const scoreJson = lobby.scores;
  let result = [];
  for (score of scoreJson) {
    result.push([score.player.user.username, score.score]);
  }

  return result;
}

async function closeLobby() {
  await lobby.closeLobby();
  await client.disconnect();
  process.exit();
}

function createListeners(matchID, raidNum, stage, team, maxMaps) {
  lobby.on("playerJoined", (obj) => {
    const name = obj.player.user.username;
    timeout = false;
    log(`Player ${name} has joined!\n`);

    if (obj.player.user.isClient()) {
      lobby.setHost("#" + obj.player.user.id);
    } else {
      joinIds(team).then((value) => {
        for (player of value['rows']) {
          if (player['user_id'] === obj.player.user.id) {
            playerInTeam = true;
            break;
          }
        }
      });
      channel.sendMessage(`Welcome ${name}!`);
    }
  });

  lobby.on("allPlayersReady", (obj) => {
    let slots = lobby.slots.filter(n => n);
    
    if (slots.length < 2) {
      channel.sendMessage("Not enough players to start the match!");
    } else {
        log("-# All players are ready, starting match...\n");
        channel.sendMessage("All players are ready, starting match in 10 seconds!");
        channel.sendMessage("Type .abort if you would like to abort the timer.");
        lobby.startMatch(10);
      }
  });

  lobby.on("matchFinished", async () => {
    mapIndex++;
    setTimeout(updatePlayedMap, 5000, mapOrder[mapsPlayed][0], raidNum, stage, team);

    compareScore(mapIndex - 1).then((value) => {
      if (value == false) {
        mapsPlayed++;
        
        log("Current map did not count as a clear.\n");
        channel.sendMessage(
          "This map did not count as a clear! You will have to play an extra map.",
        );
        setBeatmap(mapOrder[mapsPlayed][0], mapOrder[mapsPlayed][1]);
      } else {
        mapsPlayed++;
        mapsCleared++;
        firstScore = true;

        getScoreData().then((value) => {
          idsToUsername(value).then((scores) => {
            player = 1;
            for (score of scores) {
              if (firstScore) {
                firstScore = false;
                firstIndex = scoreIndex;
              }

              data[0][scoreIndex] = score[1];
              scoreIndex++;
              updateDBScores(mapOrder[mapsPlayed-1][0], raidNum, stage, team, score[1], score[0], mapsCleared, player);
              player++;
            }
          });
          scoreIndex = firstIndex + cellIncrement;
        });

        if (mapsCleared < maxMaps) {
          channel.sendMessage("Map complete, score has been recorded!");
          setBeatmap(mapOrder[mapsPlayed][0], mapOrder[mapsPlayed][1]);
        } else if (mapsCleared >= maxMaps) {
          setTimeout(updateData, 10000);
          
          setTimeout(log, 5000, "-# Closing lobby and disconnecting...\n");
          channel.sendMessage(
            "Raid has been completed! GGWP! Closing lobby in 1 minute...",
          );
          getCurrentBonus(team).then((value) => {
            updateRaidBonus(team, matchID, value.rows[0].raid_bonus);
          });
          setTimeout(closeLobby, 60000);
        }
      }
    });
  });

  lobby.on("playerLeft", (obj) => {
    const name = obj.user.ircUsername;
    log(`-# ${name} has disconnected.\n`);
  });

  channel.on("message", async (msg) => {
    if (msg.message[0] !== ".") return;

    const command = msg.message.split(" ")[0].toLowerCase();

    switch (command) {
      case prefix + "abort":
        lobby.abortTimer();
        log("Timer has been aborted.\n");
        channel.sendMessage("Timer has been aborted.");
    }
  });

  client.on("PM", async (msg) => {
    if (msg.message[0] !== ".") return;

    const command = msg.message.split(" ")[0].toLowerCase();

    switch (command) {
      case prefix + "invite":
        joinIds(team).then((value) => {
          usernameToID(msg.user.ircUsername).then((value2) => {
            for (player of value['rows']) {
              if (value2.user_id.toString() === player['user_id']) {
                log(`-# Inviting ${msg.user.ircUsername}\n`);
                lobby.invitePlayer(`#${player['user_id']}`);
                break
              }
            }
          });
        });
    }
  });
}