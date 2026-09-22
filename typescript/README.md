F72 Explore Typescript compatiblity of javascript code
nono.ts is the TypeScript port of static/js/nonosweeper.js. It lived at
static/js/nono.js — inside the served, auto-minified asset tree — until
2026-09-22, when it was moved here (F-ASSETS).

    tsc nono.ts
No errors.  

However if you replace nonosweeper.js with nono.js the javascript
console throws errors.

