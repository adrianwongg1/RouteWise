import { StackScreenProps } from "@react-navigation/stack";
import { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { RootStackParamList } from "../../App";
import { predict } from "../api/predict";

type Props = StackScreenProps<RootStackParamList, "Search">;
type Mode = "flight" | "route";

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const TIME_RE = /^\d{2}:\d{2}$/;

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function SearchScreen({ navigation }: Props) {
  const [mode, setMode] = useState<Mode>("flight");
  const [flightIata, setFlightIata] = useState("");
  const [flightDate, setFlightDate] = useState(todayISO());
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [departureTime, setDepartureTime] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onCheck() {
    setError(null);
    const date = flightDate.trim();
    if (!DATE_RE.test(date)) {
      setError("Invalid date — use YYYY-MM-DD, e.g. 2026-04-20");
      return;
    }
    if (mode === "route" && !TIME_RE.test(departureTime.trim())) {
      setError("Invalid time — use HH:MM, e.g. 09:15");
      return;
    }

    const payload =
      mode === "flight"
        ? { flight_iata: flightIata.trim().toUpperCase(), flight_date: date }
        : {
            origin: origin.trim().toUpperCase(),
            destination: destination.trim().toUpperCase(),
            flight_date: date,
            departure_time: departureTime.trim(),
          };

    try {
      setLoading(true);
      const prediction = await predict(payload);
      navigation.navigate("Result", { prediction, flightDate: date });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  const disabled =
    loading ||
    !flightDate.trim() ||
    (mode === "flight"
      ? !flightIata.trim()
      : !origin.trim() || !destination.trim() || !departureTime.trim());

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.scroll}
        keyboardShouldPersistTaps="handled"
      >
        <Text style={styles.title}>Predict your delay risk</Text>
        <Text style={styles.subtitle}>Enter your flight details</Text>

        <View style={styles.segmented}>
          <Segment
            label="Flight #"
            active={mode === "flight"}
            onPress={() => setMode("flight")}
          />
          <Segment
            label="Route"
            active={mode === "route"}
            onPress={() => setMode("route")}
          />
        </View>

        {mode === "flight" ? (
          <>
            <Field label="Flight number">
              <TextInput
                value={flightIata}
                onChangeText={setFlightIata}
                placeholder="AA101"
                autoCapitalize="characters"
                style={styles.input}
              />
            </Field>
            <Field label="Flight date (YYYY-MM-DD)">
              <TextInput
                value={flightDate}
                onChangeText={setFlightDate}
                placeholder="2026-04-20"
                autoCapitalize="none"
                style={styles.input}
              />
            </Field>
          </>
        ) : (
          <>
            <Field label="Origin airport">
              <TextInput
                value={origin}
                onChangeText={setOrigin}
                placeholder="LAX"
                autoCapitalize="characters"
                style={styles.input}
              />
            </Field>
            <Field label="Destination airport">
              <TextInput
                value={destination}
                onChangeText={setDestination}
                placeholder="JFK"
                autoCapitalize="characters"
                style={styles.input}
              />
            </Field>
            <Field label="Flight date (YYYY-MM-DD)">
              <TextInput
                value={flightDate}
                onChangeText={setFlightDate}
                placeholder="2026-04-20"
                autoCapitalize="none"
                style={styles.input}
              />
            </Field>
            <Field label="Departure time (HH:MM)">
              <TextInput
                value={departureTime}
                onChangeText={setDepartureTime}
                placeholder="09:15"
                autoCapitalize="none"
                style={styles.input}
              />
            </Field>
          </>
        )}

        {error && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        <Pressable
          style={[styles.button, disabled && styles.buttonDisabled]}
          onPress={onCheck}
          disabled={disabled}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Check Delay Risk</Text>
          )}
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function Segment({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      style={[styles.segment, active && styles.segmentActive]}
      onPress={onPress}
    >
      <Text style={[styles.segmentText, active && styles.segmentTextActive]}>
        {label}
      </Text>
    </Pressable>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  scroll: { padding: 20, paddingBottom: 40 },
  title: { fontSize: 26, fontWeight: "800", color: "#0f172a" },
  subtitle: { fontSize: 14, color: "#475569", marginTop: 6, marginBottom: 20 },
  segmented: {
    flexDirection: "row",
    backgroundColor: "#e2e8f0",
    borderRadius: 10,
    padding: 4,
    marginBottom: 20,
  },
  segment: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: "center",
  },
  segmentActive: { backgroundColor: "#fff" },
  segmentText: { fontSize: 14, fontWeight: "600", color: "#475569" },
  segmentTextActive: { color: "#0f172a" },
  field: { marginBottom: 14 },
  fieldLabel: {
    fontSize: 13,
    fontWeight: "600",
    color: "#334155",
    marginBottom: 6,
  },
  input: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#cbd5e1",
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    color: "#0f172a",
  },
  button: {
    marginTop: 12,
    backgroundColor: "#0f172a",
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: "center",
  },
  buttonDisabled: { backgroundColor: "#94a3b8" },
  buttonText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  errorBox: {
    backgroundColor: "#fee2e2",
    borderRadius: 10,
    padding: 12,
    marginBottom: 10,
  },
  errorText: { color: "#b91c1c", fontSize: 14 },
});
