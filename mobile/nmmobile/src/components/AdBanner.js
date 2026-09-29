import React from 'react';
import { View, StyleSheet } from 'react-native';
import { BannerAd, BannerAdSize, TestIds } from 'react-native-google-mobile-ads';
import { Platform } from 'react-native';

// Replace these with your Numbers Match–specific ad unit IDs from AdMob
const AD_UNIT_ID = __DEV__
  ? TestIds.BANNER
  : Platform.OS === 'ios'
    ? 'ca-app-pub-8102958922361899/1016578124'
    : 'ca-app-pub-8102958922361899/1016578124';

export default function AdBanner() {
  return (
    <View style={styles.container}>
      <BannerAd unitId={AD_UNIT_ID} size={BannerAdSize.BANNER} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: 'center' },
});
