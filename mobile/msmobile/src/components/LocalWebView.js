/**
 * LocalWebView.js
 *
 * Loads a bundled HTML asset and renders it in a WebView.
 * The asset must be required at the call site (Metro resolves require()
 * statically, so it can't be called with a variable).
 *
 * Usage:
 *   <LocalWebView assetModule={require('../../assets/howtoplay_content.html')} />
 *
 * Asset loading is async: shows an ActivityIndicator while the asset URI
 * is resolved, then switches to the WebView.
 */

import React, { useState, useEffect } from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { WebView } from 'react-native-webview';
import { Asset } from 'expo-asset';
import { useTheme } from '../context/ThemeContext';

export default function LocalWebView({ assetModule }) {
  const { theme } = useTheme();
  const [uri, setUri] = useState(null);

  useEffect(() => {
    Asset.fromModule(assetModule)
      .downloadAsync()
      .then(asset => setUri(asset.localUri));
  }, [assetModule]);

  if (!uri) {
    return (
      <View style={[styles.center, { backgroundColor: theme.background }]}>
        <ActivityIndicator color={theme.accent} />
      </View>
    );
  }

  return (
    <WebView
      source={{ uri }}
      style={{ backgroundColor: theme.background }}
      originWhitelist={['*']}
      showsVerticalScrollIndicator={false}
    />
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
});
