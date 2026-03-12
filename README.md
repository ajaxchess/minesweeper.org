https://minesweeper.org  
Website where you can play minesweeper in your browser.  
Daily high scores are saved in the database.

https://github.com/ajaxchess/minesweeper.org Written by Richard Cross

move database_template.py to database.py and update your credentials

CREATE DATABASE minesweeper CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'the_minesweeper_user'@'localhost' IDENTIFIED BY 'the_password';
GRANT ALL PRIVILEGES ON minesweeper.* TO 'the_minesweeper_user'@'localhost';
FLUSH PRIVILEGES;

If you change requirements.txt, you need to reinstall
cd ~/minesweeper
source venv/bin/activate
pip install -r requirements.txt

sudo systemctl restart minesweeper

The start script looks like this:
systemctl cat minesweeper
# /etc/systemd/system/minesweeper.service
[Unit]
Description=Minesweeper FastAPI App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/minesweeper
ExecStart=/home/ubuntu/minesweeper/venv/bin/uvicorn main:app --host 127.0.0.1 ->
Restart=always

[Install]
WantedBy=multi-user.target

To debug the uvicorn application, this command is useful:
sudo journalctl -u minesweeper -f

[About]
Minesweeper.org was originally launched in 2001 and was dedicated to Diana, the Princess of
Wales and the charity she supported, the HALO Truse.
https://www.halousa.org/

The original website can be seen here:
https://web.archive.org/web/20040325004955/http://www.minesweeper.org/
One goal of this project is to bring back the original website look, feel, and mission.
