/**
 * AdBanner.js
 *
 * Anchored adaptive banner ad using Google Mobile Ads.
 *
 * Ad unit IDs below are Google's test IDs.
 * TODO before production release: replace with real ad unit IDs from AdMob console:
 *   Publisher: ca-app-pub-8102958922361899
 *   iOS ad unit:     ca-app-pub-8102958922361899/XXXXXXXXXX
 *   Android ad unit: ca-app-pub-8102958922361899/XXXXXXXXXX
 *
 * Also replace the androidAppId / iosAppId in app.json with real App IDs:
 *   ca-app-pub-8102958922361899~XXXXXXXXXX (iOS)
 *   ca-app-pub-8102958922361899~XXXXXXXXXX (Android)
 */

import React from 'react';
import { View, Platform, StyleSheet } from 'react-native';
import { BannerAd, BannerAdSize } from 'react-native-google-mobile-ads';

// Test ad unit ID — same for both platforms during development
// ca-app-pub-3940256099942544/9214589741 is Google's official test adaptive banner
const AD_UNIT_ID = Platform.select({
  ios:     'ca-app-pub-3940256099942544/9214589741',
  android: 'ca-app-pub-3940256099942544/9214589741',
});

export default function AdBanner() {
  return (
    <View style={styles.container}>
      <BannerAd
        unitId={AD_UNIT_ID}
        size={BannerAdSize.ANCHORED_ADAPTIVE_BANNER}
        requestOptions={{ requestNonPersonalizedAdsOnly: false }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems:      'center',
    justifyContent:  'center',
    width:           '100%',
  },
});
