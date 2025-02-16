const Banchojs = require("bancho.js");

const config = require('./config.json');
var pg = require('pg');
var conString = `${process.env.CONSTRING}`;

var pgClient = new pg.Client(conString);
pgClient.connect();
console.log("Connected to PostgreSQL");

const client = new Banchojs.BanchoClient(config);

async function getRaid() {
    raid = pgClient.query(`SELECT * FROM temp;`);

    return raid;
}

async function deleteTemp() {

}

async function closeLobby() {
    let mpLobby = client.getChannel(`CRTOA: Raid #${raidNum}: (${stage} / ${matchID} / ${team})`).lobby;
    await mpLobby.closeLobby();
    await client.disconnect();
    process.exit();
}