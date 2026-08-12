import { StyleSheet, Text, View } from 'react-native';

type Props = { explanation: string };

export default function ExplanationCard({ explanation }: Props) {
  return (
    <View style={styles.card}>
      <Text style={styles.label}>Why this risk?</Text>
      <Text style={styles.body}>{explanation}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#f1f5f9',
    borderRadius: 14,
    padding: 16,
  },
  label: {
    fontSize: 12,
    fontWeight: '700',
    color: '#64748b',
    letterSpacing: 0.8,
    marginBottom: 6,
  },
  body: { fontSize: 15, lineHeight: 22, color: '#0f172a' },
});
