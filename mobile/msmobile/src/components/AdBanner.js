/**
 * AdBanner.js
 *
 * Anchored adaptive banner ad using Google Mobile Ads.
 *
 * Pass a new `refreshKey` value to reload the ad (e.g. on every win when
 * autoSubmit is enabled).  Changing the key causes React to unmount and
 * remount the BannerAd, which requests a fresh ad from AdMob.
 *
 * AdMob IDs are per platform; never reuse one platform's IDs on the other.
 *   iOS:     app ca-app-pub-8102958922361899~3782342262, banner .../1016578124
 *   Android: app ca-app-pub-8102958922361899~6698276763, banner .../4239634384
 * The app IDs are set in app.json (react-native-google-mobile-ads plugin).
 */

import React from 'react';
import { View, Platform, StyleSheet } from 'react-native';
import { BannerAd, BannerAdSize } from 'react-native-google-mobile-ads';

const AD_UNIT_ID = Platform.select({
  ios:     'ca-app-pub-8102958922361899/1016578124',
  android: 'ca-app-pub-8102958922361899/4239634384',
});

export default function AdBanner({ refreshKey = 0 }) {
  return (
    <View style={styles.container}>
      <BannerAd
        key={refreshKey}
        unitId={AD_UNIT_ID}
        size={BannerAdSize.ANCHORED_ADAPTIVE_BANNER}
        requestOptions={{ requestNonPersonalizedAdsOnly: false }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems:     'center',
    justifyContent: 'center',
    width:          '100%',
  },
});
