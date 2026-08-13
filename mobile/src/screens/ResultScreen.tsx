import { StackScreenProps } from '@react-navigation/stack';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { RootStackParamList } from '../../App';
import { usePushToken } from '../../App';
import { subscribe } from '../api/subscribe';
import ExplanationCard from '../components/ExplanationCard';
import FlightCard from '../components/FlightCard';
import RiskBadge from '../components/RiskBadge';
import { PredictResponse } from '../types';

type Props = StackScreenProps<RootStackParamList, 'Result'>;

function extractTime(value: string | null): string {
  if (!value) return '00:00';
  // Handle ISO strings like "2026-04-19T08:00:00Z" or plain "HH:MM"
  const m = /T(\d{2}:\d{2})/.exec(value) ?? /^(\d{1,2}:\d{2})/.exec(value);
  return m ? m[1] : '00:00';
}

// Result has a real URL now (see App.tsx's `linking` config), so it can be
// hit directly, bookmarked, or reloaded. The prediction object doesn't
// round-trip through a URL query string — React Navigation stringifies it
// as the literal text "[object Object]" and never parses it back, so
// `route.params` on a fresh load is present but garbage, not absent.
// Checking the actual shape (not just truthiness) is what catches that.
function isValidResultParams(
  params: unknown
): params is { prediction: PredictResponse; flightDate: string } {
  if (!params || typeof params !== 'object') return false;
  const { prediction, flightDate } = params as Record<string, unknown>;
  return (
    !!prediction &&
    typeof prediction === 'object' &&
    'risk_level' in prediction &&
    'predicted_probability' in prediction &&
    typeof flightDate === 'string'
  );
}

export default function ResultScreen({ route, navigation }: Props) {
  const pushToken = usePushToken();
  const [loading, setLoading] = useState(false);
  const [subscribed, setSubscribed] = useState(false);
  const hasValidParams = isValidResultParams(route.params);

  useEffect(() => {
    if (!hasValidParams) {
      navigation.replace('Search');
    }
  }, [hasValidParams, navigation]);

  if (!isValidResultParams(route.params)) {
    return null;
  }

  const { prediction, flightDate } = route.params;

  async function onSubscribe() {
    if (!pushToken) {
      Alert.alert(
        'Notifications not enabled',
        'Please allow notifications in your device settings to get delay alerts.'
      );
      return;
    }
    try {
      setLoading(true);
      await subscribe({
        push_token: pushToken,
        flight_iata: prediction.flight_iata,
        flight_date: flightDate,
        origin: prediction.origin,
        destination: prediction.destination,
        airline: prediction.airline,
        scheduled_departure: extractTime(prediction.scheduled_departure),
        predicted_risk: prediction.predicted_probability,
      });
      setSubscribed(true);
    } catch (e: unknown) {
      Alert.alert('Subscribe failed', e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.scroll}
      keyboardShouldPersistTaps="handled"
    >
      <FlightCard
        flightIata={prediction.flight_iata}
        airline={prediction.airline}
        origin={prediction.origin}
        destination={prediction.destination}
        scheduledDeparture={prediction.scheduled_departure}
        currentStatus={prediction.current_status}
        currentDelayMinutes={prediction.current_delay_minutes}
      />

      <View style={styles.spacer} />
      <RiskBadge level={prediction.risk_level} probability={prediction.predicted_probability} />
      <View style={styles.spacer} />
      <ExplanationCard explanation={prediction.explanation} />
      <View style={styles.spacer} />

      {subscribed ? (
        <View style={styles.confirmed}>
          <Text style={styles.confirmedTitle}>You're subscribed ✅</Text>
          <Text style={styles.confirmedBody}>
            You'll get a confirmation now. This version doesn't track live status changes yet —
            check back here before you fly for an updated risk estimate.
          </Text>
        </View>
      ) : Platform.OS === 'web' ? (
        <View style={styles.webCard}>
          <Text style={styles.subscribeTitle}>Get flight alerts</Text>
          <Text style={styles.subscribeBody}>
            Download the RouteWise app on your iPhone to get push notifications for this flight.
          </Text>
        </View>
      ) : (
        <View style={styles.subscribeCard}>
          <Text style={styles.subscribeTitle}>Get flight alerts</Text>
          <Text style={styles.subscribeBody}>
            We'll send a confirmation now with your current risk estimate. This version doesn't
            track live status changes yet.
          </Text>
          <Pressable
            style={[styles.button, (loading || !pushToken) && styles.buttonDisabled]}
            onPress={onSubscribe}
            disabled={loading || !pushToken}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>
                {pushToken ? 'Subscribe for alerts' : 'Enable notifications to subscribe'}
              </Text>
            )}
          </Pressable>
        </View>
      )}

      <View style={styles.spacer} />
      <Pressable style={styles.searchAgainButton} onPress={() => navigation.navigate('Search')}>
        <Text style={styles.searchAgainText}>Search another flight</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  scroll: { padding: 20, paddingBottom: 40 },
  spacer: { height: 16 },
  subscribeCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  subscribeTitle: { fontSize: 18, fontWeight: '700', color: '#0f172a' },
  subscribeBody: { fontSize: 14, color: '#475569', marginTop: 6, marginBottom: 14 },
  button: {
    backgroundColor: '#0f172a',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  buttonDisabled: { backgroundColor: '#94a3b8' },
  buttonText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  confirmed: { backgroundColor: '#dcfce7', borderRadius: 16, padding: 20 },
  confirmedTitle: { fontSize: 18, fontWeight: '800', color: '#166534' },
  confirmedBody: { fontSize: 14, color: '#166534', marginTop: 8, lineHeight: 20 },
  searchAgainButton: {
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#cbd5e1',
  },
  searchAgainText: { color: '#334155', fontSize: 15, fontWeight: '600' },
  webCard: {
    backgroundColor: '#eff6ff',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: '#bfdbfe',
  },
});
