const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// Allow Metro to bundle .html files as assets so WebView screens can
// load howtoplay_content.html and strategy_content.html via Asset.fromModule().
config.resolver.assetExts.push('html');

module.exports = config;
