const { withDangerousMod } = require('@expo/config-plugins');
const fs = require('fs');
const path = require('path');

const withAdiRegistration = (config) => {
  return withDangerousMod(config, [
    'android',
    (config) => {
      const destDir = path.join(config.modRequest.platformProjectRoot, 'app', 'src', 'main', 'assets');
      fs.mkdirSync(destDir, { recursive: true });
      fs.copyFileSync(
        path.join(config.modRequest.projectRoot, 'assets', 'adi-registration.properties'),
        path.join(destDir, 'adi-registration.properties')
      );
      return config;
    },
  ]);
};

module.exports = withAdiRegistration;
