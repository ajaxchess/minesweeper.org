There are 48 teams in the 2026 world cup.  I want to make a Tametsi 2026 World Cup Celebration page.
We will need a link in the menu and a banner if you haven't set your fan flag.
Your fan flag is the flag that will display on all scores in the 2026worldcup tree.
Your country flag is the flag of your home country and that will still display if you play regular minesweeper on the associated high score list for that game.

There will be a new database field, the 2026 fan flag, which is selected among the 48 teams in the cup.
You can set this in your profile or on any of the pages in the 2026worldcup tree

**Implementation note (2026-05-10):** The fan flag selector is live on the profile page (`/profile`).
- Database table: `user_profiles`
- Database column: `2026_world_cup_fan_flag` (VARCHAR 16, nullable)
- Python model attribute: `UserProfile.wc2026_fan` (mapped via SQLAlchemy `name=` parameter)
- API endpoint: `POST /api/profile/wc2026-fan`

There's a little ambiguity in this document.  Each country is playing games in the world cup.  We want to keep everyone up-to-date on how those games are going.
So the https://minesweeper.org/2026worldcup will have all the latest world cup news.  What games are coming up.  What scores have happened already.  Which teams
are winning their groups.  We will be providing that data and that will update the content for the main page and the teams page.

There is also a fan event where fans play Tametsi.  The site will track how many games the fans win and will have leaderboards for fans and for country.

So 
minesweeper.org/2026worldcup
minesweeper.org/2026worldcup/algeria
...
minesweeper.org/2026worldcup/uzbekistan

Each page will have information about the country and a list of when they are playing.

There should be a main page with a list of all the groups and all the countries in the group.
The countries should be clickable so that you to to that page's homepage.

If the user logs in, they should be able to set their preferred time zone.
Then the country game times will show in that time zone.

We will focus on the group stage.  The idea is to have a web page that has all 48 teams.  You can click on a country and you get a Tametsi game that uses the colors of that team.
The country page will list the other countries in the group and when that team will play their group games.
There will be a Tametsi board on each countries home page.  The standard board will be (no guess)
15 squares (x) and 9 squares (y)  The country's primary color will fill the top 5 squares and the secondary color will fill the bottom 4 squares.  There will be 20 mines.
Whenever you flag a mine, the flag icon will be the fan flag of your selected world cup favorite team.
The Tametsi rules will be:  There will be a white number which is the total number of mines on that row or column.  Above or to the left will be a green number which is the number of mines
that have not yet been flagged on that row or column.  Above and to the left of the board will be a count of the number of unflagged mines in the part of the board with the primary or secondary color.
There will be a starting x on the top left of the board.
You can also select a Tametsi hard board and you will get a board of 30x18 with 99 mines.  This should also be no guess. Hard will have the top 9 rows be the primary color and the bottom 9 rows be the secondary
color for that team.

For example:
Canada upper 5 rows will be in Red (FF0000) and the bottom 4 rows will be in White (FFFFFF).
3 (red)
3 (white)
    141 (green)
    141 (white)
1 1 oxo
0 0 ooo
0 0 ooo
0 1 oxo
0 1 oxo
...
2 2 xox
0 0 ooo
1 1 oxo
0 0 ooo

There would be two numbers above and the the left of the board: a Red 3 and a White 3
Suppose the player flags mine at 1,9.  The green 4 -> 3.  The red 3 -> 2.  The flag displayed over the mine would be a Canadian flag

Each country will have a leaderboard for that country.  Users who are logged in will have their scores stay on the leaderboard during the entire period of the World Cup.

Please put a note on each country page regarding if they are a signatory to the Ottawa Treaty and have a link out to the wikipedia page:
https://en.wikipedia.org/wiki/Ottawa_Treaty
Status                 Nations
Signatories / Parties, "Algeria, Argentina, Australia, Austria, Belgium, Bosnia & Herzegovina, Brazil, Canada, Cape Verde, Colombia, Croatia, Czechia, DR Congo, Ecuador, France, Germany, Ghana, Haiti, Iraq, Ivory Coast, Japan, Jordan, Mexico, Netherlands, New Zealand, Norway, Panama, Paraguay, Portugal, Senegal, South Africa, Spain, Sweden, Switzerland, Tunisia, Türkiye, United Kingdom (England, Scotland), Uruguay."
Non-Signatories,       "Egypt, Iran, Morocco, Saudi Arabia, South Korea, USA, Uzbekistan."


Here are the countries:

Nation,Primary Hex,Primary RGB,Secondary Hex,Secondary RGB
Algeria,#FFFFFF,"(255, 255, 255)",#006233,"(0, 98, 51)"
Argentina,#75AADB,"(117, 170, 219)",#FFFFFF,"(255, 255, 255)"
Australia,#FFCD00,"(255, 205, 0)",#005031,"(0, 80, 49)"
Austria,#ED2939,"(237, 41, 57)",#FFFFFF,"(255, 255, 255)"
Belgium,#BA0C2F,"(186, 12, 47)",#FFCD00,"(255, 205, 0)"
Bosnia & Herz.,#002395,"(0, 35, 149)",#FECB00,"(254, 203, 0)"
Brazil,#FFDF00,"(255, 223, 0)",#009B3A,"(0, 155, 58)"
Canada,#FF0000,"(255, 0, 0)",#FFFFFF,"(255, 255, 255)"
Cape Verde,#003893,"(0, 56, 147)",#F7D117,"(247, 209, 23)"
Colombia,#FCD116,"(252, 209, 22)",#003893,"(0, 56, 147)"
Croatia,#FF0000,"(255, 0, 0)",#FFFFFF,"(255, 255, 255)"
Curaçao,#002B7F,"(0, 43, 127)",#F9D616,"(249, 214, 22)"
Czech Republic,#ED1B24,"(237, 27, 36)",#11457E,"(17, 69, 126)"
DR Congo,#007FFF,"(0, 127, 255)",#F7D117,"(247, 209, 23)"
Ecuador,#FFDD00,"(255, 221, 0)",#034EA2,"(3, 78, 162)"
Egypt,#E20111,"(226, 1, 17)",#000000,"(0, 0, 0)"
England,#FFFFFF,"(255, 255, 255)",#000040,"(0, 0, 64)"
France,#21304D,"(33, 48, 77)",#ED2939,"(237, 41, 57)"
Germany,#FFFFFF,"(255, 255, 255)",#000000,"(0, 0, 0)"
Ghana,#FFFFFF,"(255, 255, 255)",#000000,"(0, 0, 0)"
Haiti,#00209F,"(0, 32, 159)",#D21034,"(210, 16, 52)"
Iran,#FFFFFF,"(255, 255, 255)",#DA291C,"(218, 41, 28)"
Iraq,#007A33,"(0, 122, 51)",#FFFFFF,"(255, 255, 255)"
Ivory Coast,#FF8200,"(255, 130, 0)",#009E60,"(0, 158, 96)"
Japan,#000555,"(0, 5, 85)",#FFFFFF,"(255, 255, 255)"
Jordan,#FFFFFF,"(255, 255, 255)",#CE1126,"(206, 17, 38)"
Mexico,#006847,"(0, 104, 71)",#FFFFFF,"(255, 255, 255)"
Morocco,#C1272D,"(193, 39, 45)",#006233,"(0, 98, 51)"
Netherlands,#FF4F00,"(255, 79, 0)",#FFFFFF,"(255, 255, 255)"
New Zealand,#FFFFFF,"(255, 255, 255)",#000000,"(0, 0, 0)"
Norway,#EF2B2D,"(239, 43, 45)",#002868,"(0, 40, 104)"
Panama,#DA121A,"(218, 18, 26)",#072357,"(7, 35, 87)"
Paraguay,#D52B1E,"(213, 43, 30)",#FFFFFF,"(255, 255, 255)"
Portugal,#E42518,"(228, 37, 24)",#046A38,"(4, 106, 56)"
Qatar,#8A1538,"(138, 21, 56)",#FFFFFF,"(255, 255, 255)"
Saudi Arabia,#006C35,"(0, 108, 53)",#FFFFFF,"(255, 255, 255)"
Scotland,#002D56,"(0, 45, 86)",#FFFFFF,"(255, 255, 255)"
Senegal,#FFFFFF,"(255, 255, 255)",#11A335,"(17, 163, 53)"
South Africa,#FFCD00,"(255, 205, 0)",#007A33,"(0, 122, 51)"
South Korea,#ED1C24,"(237, 28, 36)",#000000,"(0, 0, 0)"
Spain,#C60B1E,"(198, 11, 30)",#FFC400,"(255, 196, 0)"
Sweden,#FECC00,"(254, 204, 0)",#006AA7,"(0, 106, 167)"
Switzerland,#D52B1E,"(213, 43, 30)",#FFFFFF,"(255, 255, 255)"
Tunisia,#FFFFFF,"(255, 255, 255)",#E70013,"(231, 0, 19)"
Türkiye,#E30A17,"(227, 10, 23)",#FFFFFF,"(255, 255, 255)"
Uruguay,#75AADB,"(117, 170, 219)",#000000,"(0, 0, 0)"
USA,#FFFFFF,"(255, 255, 255)",#002868,"(0, 40, 104)"
Uzbekistan,#FFFFFF,"(255, 255, 255)",#0099B5,"(0, 153, 181)"

Here are the group stage matches:
Group,Match Date,Matchup,Time (CDT),City,Status
Group A,June 11,Mexico vs. South Africa,2:00 PM,Mexico City,Scheduled
Group A,June 11,South Korea vs. Czechia,9:00 PM,Guadalajara,Scheduled
Group A,June 16,Mexico vs. South Korea,5:00 PM,Monterrey,Scheduled
Group A,June 16,Czechia vs. South Africa,8:00 PM,Seattle,Scheduled
Group A,June 24,Czechia vs. Mexico,8:00 PM,Mexico City,Scheduled
Group A,June 24,South Africa vs. South Korea,8:00 PM,Monterrey,Scheduled
Group B,June 12,Canada vs. Bosnia & Herz.,2:00 PM,Toronto,Scheduled
Group B,June 13,Qatar vs. Switzerland,2:00 PM,Vancouver,Scheduled
Group B,June 17,Canada vs. Qatar,12:00 PM,Toronto,Scheduled
Group B,June 17,Switzerland vs. Bosnia & Herz.,8:00 PM,Vancouver,Scheduled
Group B,June 24,Switzerland vs. Canada,2:00 PM,Vancouver,Scheduled
Group B,June 24,Bosnia & Herz. vs. Qatar,2:00 PM,Toronto,Scheduled
Group C,June 13,Brazil vs. Morocco,5:00 PM,Miami,Scheduled
Group C,June 13,Haiti vs. Scotland,8:00 PM,New York/New Jersey,Scheduled
Group C,June 18,Brazil vs. Haiti,2:00 PM,Atlanta,Scheduled
Group C,June 18,Scotland vs. Morocco,5:00 PM,Miami,Scheduled
Group C,June 24,Scotland vs. Brazil,11:00 AM,Miami,Scheduled
Group C,June 24,Morocco vs. Haiti,11:00 AM,Atlanta,Scheduled
Group D,June 12,USA vs. Paraguay,8:00 PM,Los Angeles,Scheduled
Group D,June 13,Australia vs. Türkiye,11:00 PM,Seattle,Scheduled
Group D,June 19,USA vs. Australia,8:00 PM,Seattle,Scheduled
Group D,June 19,Türkiye vs. Paraguay,5:00 PM,San Francisco,Scheduled
Group D,June 25,Türkiye vs. USA,8:00 PM,Los Angeles,Scheduled
Group D,June 25,Paraguay vs. Australia,8:00 PM,San Francisco,Scheduled
Group E,June 14,Germany vs. Curaçao,12:00 PM,Kansas City,Scheduled
Group E,June 14,Ivory Coast vs. Ecuador,6:00 PM,Dallas,Scheduled
Group E,June 20,Germany vs. Ivory Coast,2:00 PM,Kansas City,Scheduled
Group E,June 20,Ecuador vs. Curaçao,11:00 AM,Dallas,Scheduled
Group E,June 25,Ecuador vs. Germany,2:00 PM,Dallas,Scheduled
Group E,June 25,Curaçao vs. Ivory Coast,2:00 PM,Kansas City,Scheduled
Group F,June 14,Netherlands vs. Japan,3:00 PM,Houston,Scheduled
Group F,June 14,Sweden vs. Tunisia,9:00 PM,Monterrey,Scheduled
Group F,June 20,Netherlands vs. Sweden,8:00 PM,Houston,Scheduled
Group F,June 20,Tunisia vs. Japan,5:00 PM,Guadalajara,Scheduled
Group F,June 25,Tunisia vs. Netherlands,11:00 AM,Houston,Scheduled
Group F,June 25,Japan vs. Sweden,11:00 AM,Monterrey,Scheduled
Group G,June 15,Belgium vs. Egypt,2:00 PM,Boston,Scheduled
Group G,June 15,Iran vs. New Zealand,8:00 PM,Philadelphia,Scheduled
Group G,June 21,Belgium vs. Iran,11:00 AM,Philadelphia,Scheduled
Group G,June 21,New Zealand vs. Egypt,2:00 PM,Boston,Scheduled
Group G,June 26,New Zealand vs. Belgium,8:00 PM,Boston,Scheduled
Group G,June 26,Egypt vs. Iran,8:00 PM,Philadelphia,Scheduled
Group H,June 15,Spain vs. Cape Verde,11:00 AM,Los Angeles,Scheduled
Group H,June 15,Saudi Arabia vs. Uruguay,5:00 PM,San Francisco,Scheduled
Group H,June 21,Spain vs. Saudi Arabia,8:00 PM,Los Angeles,Scheduled
Group H,June 21,Uruguay vs. Cape Verde,5:00 PM,San Francisco,Scheduled
Group H,June 26,Uruguay vs. Spain,2:00 PM,San Francisco,Scheduled
Group H,June 26,Cape Verde vs. Saudi Arabia,2:00 PM,Los Angeles,Scheduled
Group I,June 16,France vs. Senegal,2:00 PM,New York/New Jersey,Scheduled
Group I,June 16,Iraq vs. Norway,5:00 PM,Boston,Scheduled
Group I,June 22,France vs. Iraq,12:00 PM,New York/New Jersey,Scheduled
Group I,June 22,Norway vs. Senegal,3:00 PM,Boston,Scheduled
Group I,June 26,Norway vs. France,11:00 AM,Boston,Scheduled
Group I,June 26,Senegal vs. Iraq,11:00 AM,New York/New Jersey,Scheduled
Group J,June 16,Argentina vs. Algeria,8:00 PM,Dallas,Scheduled
Group J,June 16,Austria vs. Jordan,11:00 PM,Houston,Scheduled
Group J,June 22,Argentina vs. Austria,8:00 PM,Dallas,Scheduled
Group J,June 22,Jordan vs. Algeria,5:00 PM,Houston,Scheduled
Group J,June 27,Jordan vs. Argentina,8:00 PM,Dallas,Scheduled
Group J,June 27,Algeria vs. Austria,8:00 PM,Houston,Scheduled
Group K,June 17,Portugal vs. DR Congo,12:00 PM,Miami,Scheduled
Group K,June 17,Uzbekistan vs. Colombia,9:00 PM,Atlanta,Scheduled
Group K,June 23,Portugal vs. Uzbekistan,2:00 PM,Atlanta,Scheduled
Group K,June 23,Colombia vs. DR Congo,11:00 AM,Miami,Scheduled
Group K,June 27,Colombia vs. Portugal,2:00 PM,Miami,Scheduled
Group K,June 27,DR Congo vs. Uzbekistan,2:00 PM,Atlanta,Scheduled
Group L,June 17,England vs. Croatia,3:00 PM,Toronto,Scheduled
Group L,June 17,Ghana vs. Panama,6:00 PM,Vancouver,Scheduled
Group L,June 23,England vs. Ghana,8:00 PM,Toronto,Scheduled
Group L,June 23,Panama vs. Croatia,5:00 PM,Vancouver,Scheduled
Group L,June 27,Panama vs. England,11:00 AM,Vancouver,Scheduled
Group L,June 27,Croatia vs. Ghana,11:00 AM,Toronto,Scheduled

City,Stadium,Latitude,Longitude,Country
Mexico City,Estadio Azteca,19.3029,-99.1505,Mexico
Guadalajara,Estadio Akron,20.6811,-103.4628,Mexico
Monterrey,Estadio BBVA,25.6700,-100.2447,Mexico
Toronto,BMO Field,43.6332,-79.4186,Canada
Vancouver,BC Place,49.2768,-123.1120,Canada
Los Angeles,SoFi Stadium,33.9535,-118.3390,USA
New York/New Jersey,MetLife Stadium,40.8128,-74.0742,USA
Miami,Hard Rock Stadium,25.9581,-80.2389,USA
Atlanta,Mercedes-Benz Stadium,33.7553,-84.4006,USA
Seattle,Lumen Field,47.5952,-122.3316,USA
San Francisco,Levi's Stadium,37.4033,-121.9694,USA
Dallas,AT&T Stadium,32.7473,-97.0945,USA
Houston,NRG Stadium,29.6847,-95.4107,USA
Kansas City,Arrowhead Stadium,39.0490,-94.4839,USA
Philadelphia,Lincoln Financial Field,39.9008,-75.1675,USA
Boston,Gillette Stadium,42.0909,-71.2643,USA

Tametsi fan challenge:
If you login, you can set your world cup fan flag in your profile or on any Tametsi world cup page.
You must be logged in and set your country flag to play.
If you are logged in, when you uncover a mine, your country gets a point.  When you solve board, your country gets 20 points.
The total points for each team are displayed on the team page and on a country leaderboard on the main page.

The minesweeper.org/2026worldcup page will have a welcome and how to play at the top.  Then clickable countries organized by groups.
Then the country Tametsi leaderboard.
Then the biggest fans individual leaderboard.
The countries get the points depending on what team you set on that day.  So Bill can set his fan flag as Canada on June 1st and play easy and hard games to earn 400 points for Canada.
Suppose Canada doesn't make it into the knockout phase.  On June 27th Bill changes his fan flag to Mexico.  Each Tametsi game won will need a database field for the fan flag set at time won.
If no flag is set, no points are earned.  Once you set your flag, you should have a notice at the top of every world cup page that says You are a fan of <fan flag>!
