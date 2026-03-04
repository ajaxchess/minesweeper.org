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
