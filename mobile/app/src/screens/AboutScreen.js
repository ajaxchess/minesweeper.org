/**
 * AboutScreen.js
 *
 * Spec (Outline.md):
 *   - App version
 *   - Link to https://minesweeper.org
 *   - Created by Regis.Consulting
 *   - Support: ajaxchess@gmail.com / 312-224-1752
 */

import React from 'react';
import {
  ScrollView,
  View,
  Text,
  TouchableOpacity,
  Linking,
  StyleSheet,
} from 'react-native';
import * as WebBrowser from 'expo-web-browser';
import { useTheme } from '../context/ThemeContext';
import appJson from '../../app.json';

const APP_VERSION = appJson.expo.version;

function openWebsite() {
  WebBrowser.openBrowserAsync('https://minesweeper.org');
}

function openEmail() {
  Linking.openURL('mailto:ajaxchess@gmail.com');
}

function openPhone() {
  Linking.openURL('tel:+13122241752');
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Divider({ theme }) {
  return <View style={[styles.divider, { backgroundColor: theme.border }]} />;
}

function LinkRow({ icon, label, onPress, theme }) {
  return (
    <TouchableOpacity style={styles.linkRow} onPress={onPress} activeOpacity={0.6}>
      <Text style={styles.linkIcon}>{icon}</Text>
      <Text style={[styles.linkLabel, { color: theme.accent }]}>{label}</Text>
    </TouchableOpacity>
  );
}

function Section({ title, children, theme }) {
  return (
    <View style={styles.section}>
      <Text style={[styles.sectionTitle, { color: theme.textMuted }]}>{title}</Text>
      {children}
    </View>
  );
}

// ── Screen ────────────────────────────────────────────────────────────────────

export default function AboutScreen() {
  const { theme } = useTheme();

  return (
    <ScrollView
      style={{ backgroundColor: theme.background }}
      contentContainerStyle={styles.container}
    >

      {/* ── Hero ──────────────────────────────────────────────────────── */}
      <View style={styles.hero}>
        <Text style={styles.heroIcon}>💣</Text>
        <Text style={[styles.appName, { color: theme.text }]}>Minesweeper.org</Text>
        <Text style={[styles.version, { color: theme.textMuted }]}>Version {APP_VERSION}</Text>
      </View>

      <Divider theme={theme} />

      {/* ── Visit website ─────────────────────────────────────────────── */}
      <TouchableOpacity
        style={[styles.websiteBtn, { backgroundColor: theme.accent }]}
        onPress={openWebsite}
        activeOpacity={0.8}
      >
        <Text style={[styles.websiteBtnText, { color: theme.accentText }]}>
          Visit minesweeper.org
        </Text>
      </TouchableOpacity>

      <Divider theme={theme} />

      {/* ── Creator ───────────────────────────────────────────────────── */}
      <Section title="CREATED BY" theme={theme}>
        <Text style={[styles.bodyText, { color: theme.text }]}>Regis.Consulting</Text>
      </Section>

      <Divider theme={theme} />

      {/* ── Support ───────────────────────────────────────────────────── */}
      <Section title="SUPPORT" theme={theme}>
        <LinkRow icon="✉️" label="ajaxchess@gmail.com" onPress={openEmail} theme={theme} />
        <LinkRow icon="📞" label="312-224-1752"        onPress={openPhone} theme={theme} />
      </Section>

    </ScrollView>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    paddingBottom: 48,
  },
  hero: {
    alignItems:     'center',
    paddingTop:     48,
    paddingBottom:  32,
    paddingHorizontal: 24,
  },
  heroIcon: {
    fontSize:     64,
    marginBottom: 12,
  },
  appName: {
    fontSize:     28,
    fontWeight:   '700',
    marginBottom: 6,
  },
  version: {
    fontSize: 14,
  },
  divider: {
    height:            1,
    marginHorizontal:  0,
  },
  websiteBtn: {
    marginHorizontal:  24,
    marginVertical:    24,
    paddingVertical:   14,
    borderRadius:      10,
    alignItems:        'center',
  },
  websiteBtnText: {
    fontSize:   16,
    fontWeight: '600',
  },
  section: {
    paddingHorizontal: 24,
    paddingVertical:   20,
    gap:               10,
  },
  sectionTitle: {
    fontSize:      11,
    fontWeight:    '600',
    letterSpacing: 0.8,
    marginBottom:  2,
  },
  bodyText: {
    fontSize: 16,
  },
  linkRow: {
    flexDirection: 'row',
    alignItems:    'center',
    gap:           10,
    paddingVertical: 4,
  },
  linkIcon: {
    fontSize: 18,
  },
  linkLabel: {
    fontSize: 16,
  },
});
