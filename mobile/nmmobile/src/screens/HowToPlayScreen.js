import React from 'react';
import { ScrollView, View, Text, StyleSheet, SafeAreaView } from 'react-native';
import { useTheme } from '../context/ThemeContext';

function Section({ title, children, theme }) {
  return (
    <View style={styles.section}>
      <Text style={[styles.sectionTitle, { color: theme.text }]}>{title}</Text>
      {children}
    </View>
  );
}

function Para({ text, theme }) {
  return <Text style={[styles.para, { color: theme.textDim }]}>{text}</Text>;
}

function Rule({ children, theme }) {
  return <Text style={[styles.rule, { color: theme.textDim }]}>{children}</Text>;
}

export default function HowToPlayScreen() {
  const { theme } = useTheme();
  return (
    <SafeAreaView style={[styles.root, { backgroundColor: theme.background }]}>
      <ScrollView contentContainerStyle={styles.content}>

        <Section title="Goal" theme={theme}>
          <Para theme={theme}
            text="Clear the entire board by removing all number pairs. When the board is empty you earn a +150 bonus and complete the daily puzzle."
          />
        </Section>

        <Section title="Matching Rules" theme={theme}>
          <Rule theme={theme}>• Two numbers match if they are <Text style={{ fontWeight: '700', color: theme.text }}>identical</Text> (e.g. 3 and 3) or if they <Text style={{ fontWeight: '700', color: theme.text }}>sum to 10</Text> (e.g. 3 and 7, 1 and 9).</Rule>
          <Rule theme={theme}>• They must be connected by a clear straight line — <Text style={{ fontWeight: '700', color: theme.text }}>horizontal</Text>, <Text style={{ fontWeight: '700', color: theme.text }}>vertical</Text>, or <Text style={{ fontWeight: '700', color: theme.text }}>diagonal</Text> — with only empty cells between them.</Rule>
          <Rule theme={theme}>• <Text style={{ fontWeight: '700', color: theme.text }}>Row wrap:</Text> the last cell of a row connects horizontally to the first cell of the next row. This creates extra matching opportunities.</Rule>
        </Section>

        <Section title="Scoring" theme={theme}>
          <Rule theme={theme}>⭐ <Text style={{ fontWeight: '700', color: theme.text }}>+1</Text> per pair removed.</Rule>
          <Rule theme={theme}>↔ <Text style={{ fontWeight: '700', color: theme.text }}>+1 to +4</Text> Far Apart bonus — one extra point per empty cell between the pair (max 4). Seek long-range matches!</Rule>
          <Rule theme={theme}>📏 <Text style={{ fontWeight: '700', color: theme.text }}>+10</Text> when a full row is cleared.</Rule>
          <Rule theme={theme}>🏆 <Text style={{ fontWeight: '700', color: theme.text }}>+150</Text> for clearing the entire board.</Rule>
        </Section>

        <Section title="Tools" theme={theme}>
          <Rule theme={theme}>↩ <Text style={{ fontWeight: '700', color: theme.text }}>Undo</Text> — reverses your last match. 3 per game.</Rule>
          <Rule theme={theme}>💡 <Text style={{ fontWeight: '700', color: theme.text }}>Hint</Text> — highlights one valid pair in amber. 9 per game.</Rule>
          <Rule theme={theme}>+ <Text style={{ fontWeight: '700', color: theme.text }}>Add Lines</Text> — appends the remaining numbers to the bottom, creating new adjacencies. Use when stuck. Unlimited.</Rule>
        </Section>

        <Section title="Strategy Tips" theme={theme}>
          <Rule theme={theme}>1. Scan for long-range pairs before making obvious adjacent matches — Far Apart bonuses add up fast.</Rule>
          <Rule theme={theme}>2. Target rows with only one or two numbers left to earn the +10 row-clear bonus.</Rule>
          <Rule theme={theme}>3. Save hints for genuine dead-ends, not confirmation.</Rule>
          <Rule theme={theme}>4. Use Add Lines as a last resort — more rows means more to scan.</Rule>
        </Section>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root:         { flex: 1 },
  content:      { padding: 20, gap: 4 },
  section:      { marginBottom: 20 },
  sectionTitle: { fontSize: 17, fontWeight: '700', marginBottom: 10 },
  para:         { fontSize: 14, lineHeight: 22 },
  rule:         { fontSize: 14, lineHeight: 22, marginBottom: 4 },
});
