import { StyleSheet, Text, View } from 'react-native';

import { RiskLevel } from '../types';

const COLORS: Record<RiskLevel, { bg: string; fg: string }> = {
  LOW: { bg: '#dcfce7', fg: '#166534' },
  MEDIUM: { bg: '#fef9c3', fg: '#854d0e' },
  HIGH: { bg: '#fee2e2', fg: '#991b1b' },
};

type Props = {
  level: RiskLevel;
  probability: number;
};

export default function RiskBadge({ level, probability }: Props) {
  const color = COLORS[level];
  const pct = Math.round(probability * 100);
  return (
    <View style={[styles.badge, { backgroundColor: color.bg }]}>
      <Text style={[styles.pct, { color: color.fg }]}>{pct}%</Text>
      <Text style={[styles.label, { color: color.fg }]}>{level} RISK</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignItems: 'center',
    paddingVertical: 20,
    paddingHorizontal: 24,
    borderRadius: 16,
  },
  pct: { fontSize: 48, fontWeight: '800' },
  label: { fontSize: 14, fontWeight: '700', letterSpacing: 1, marginTop: 4 },
});
