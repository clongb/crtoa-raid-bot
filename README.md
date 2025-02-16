# crtoa-raid-bot

Discord bot/Node.js chatbot for [CookieRhyme: Tour of Awesomeness](https://osu.ppy.sh/community/forums/topics/2017591?n=1).

## Python package installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install.

```bash
pip install -r requirements.txt
```

## Database setup

Install [PostgreSQL](https://www.postgresql.org/download/) for your current operating system. Currently the bot uses version 17, but you can replace 17 with whatever the latest version is in the following commands.

### Windows:

After doing the setup, start PostgreSQL by going to the bin folder (typically in `C:\Program Files\PostgreSQL\17\bin`), opening a command prompt, and running the following command (if PostgreSQL is installed in a different directory, use that path's data folder instead):

```bash
pg_ctl.exe restart -D  "C:\Program Files\PostgreSQL\17\data"
```

Open the psql app, enter your credentials (should be able to spam enter until it asks for a password), and then create the database with this query:

```bash
CREATE DATABASE cookierun;
```

### Linux:

You can also install PostgreSQL through the command line:

```bash
sudo apt install postgresql-17
```

Start PostgreSQL using:

```bash
sudo systemctl start postgresql
```

Open psql with:

```bash
sudo -u postgres psql
```

Enter credentials if you have to, and then create the database:

```bash
CREATE DATABASE cookierun;
```

## Variable setup

### Python:

#### .env:

- `DISCORD_BOT_TOKEN`: Your Discord bot's access token (obtainable from the [Discord Developer Portal](https://discord.com/developers/applications) under the `Bot` tab)
- `OSU_API_KEY`: Your osu! API key (obtainable from your [account settings page](https://osu.ppy.sh/home/account/edit#legacy-api))
- `GOOGLE_SHEET_ID`: The ID string in your data spreadsheet URL
- `POOL_SHEET_ID`: The ID string in your mappool spreadsheet URL
- `SERVICE_ACCT_FILE`: The name of your [Google service account file](https://cloud.google.com/iam/docs/keys-create-delete) (must be in the same directory) 
- `SHEET_GID`: The number at the end of the data spreadsheet URL
- `SHEET_TAB_NAME`: The spreadsheet tab name to store the raid data in
- `PLAYER_TAB`: The tab name where all the player data is kept
- `TEAM_TAB`: The tab name where all the team data is kept
- `POOL_TAB`: The tab name where all the mappools kept
- `USERNAME`: Your osu! username

#### database.ini:

Default variables are already setup, just put your postgres password in.

### JS:

- `GOOGLE_SHEET_ID`: The ID string in your data spreadsheet URL
- `SERVICE_ACCT_FILE`: The name of your [Google service account file](https://cloud.google.com/iam/docs/keys-create-delete)
- `RAID_TAB_NAME`: The spreadsheet tab name to store the raid data in
- `CONSTRING`: The string needed to connect to PostgreSQL (`postgres://usernamepassword@host:port/database`)

#### config.json:

 - `username`: Your osu! username
 - `password`: Your IRC password (obtainable from your [account settings page](https://osu.ppy.sh/home/account/edit#legacy-api))
 - `api_key`: Your osu! API key (obtainable from your [account settings page](https://osu.ppy.sh/home/account/edit#legacy-api))
 - `userId`: Your osu! UID (The numbers in your profile link)