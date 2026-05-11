import React from 'react';
import { SafeAreaView, StyleSheet } from 'react-native';
import { useTheme } from '../context/ThemeContext';
import LocalWebView from '../components/LocalWebView';

// Metro resolves require() statically — must be a literal here, not a variable.
const ASSET = require('../../assets/strategy_content.html');

export default function StrategyScreen() {
  const { theme } = useTheme();
  return (
    <SafeAreaView style={[styles.root, { backgroundColor: theme.background }]}>
      <LocalWebView assetModule={ASSET} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
});
