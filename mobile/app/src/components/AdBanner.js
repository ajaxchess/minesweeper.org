/**
 * AdBanner.js
 *
 * Anchored adaptive banner ad using Google Mobile Ads.
 *
 * TODO: replace Android ad unit with real ID once Android app is approved in AdMob:
 *   Android ad unit: ca-app-pub-8102958922361899/XXXXXXXXXX
 *   Android App ID (app.json): ca-app-pub-3940256099942544~3347511713 → real ID
 */

import React from 'react';
import { View, Platform, StyleSheet } from 'react-native';
import { BannerAd, BannerAdSize } from 'react-native-google-mobile-ads';

const AD_UNIT_ID = Platform.select({
  ios:     'ca-app-pub-8102958922361899/1016578124',
  android: 'ca-app-pub-3940256099942544/9214589741', // test ID — replace when Android is approved
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
