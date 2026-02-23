# minesweeper.org
Website where you can play minesweeper in your browser

move database_template.py to database.py and update your credentials

CREATE DATABASE minesweeper CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'the_minesweeper_user'@'localhost' IDENTIFIED BY 'the_password';
GRANT ALL PRIVILEGES ON minesweeper.* TO 'the_minesweeper_user'@'localhost';
FLUSH PRIVILEGES;
