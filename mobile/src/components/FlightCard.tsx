import { StyleSheet, Text, View } from 'react-native';

type Props = {
  flightIata: string;
  airline: string;
  origin: string;
  destination: string;
  scheduledDeparture: string | null;
  currentStatus: string | null;
  currentDelayMinutes: number | null;
};

const AIRPORT_TZ: Record<string, string> = {
  JFK: 'ET', LGA: 'ET', EWR: 'ET', BOS: 'ET', PHL: 'ET', DCA: 'ET', IAD: 'ET',
  BWI: 'ET', MIA: 'ET', FLL: 'ET', MCO: 'ET', TPA: 'ET', ATL: 'ET', CLT: 'ET',
  RDU: 'ET', DTW: 'ET', CLE: 'ET', PIT: 'ET', BDL: 'ET', ORF: 'ET', RIC: 'ET',
  ORD: 'CT', MDW: 'CT', MSP: 'CT', STL: 'CT', MCI: 'CT', MSY: 'CT', HOU: 'CT',
  IAH: 'CT', DFW: 'CT', DAL: 'CT', AUS: 'CT', SAT: 'CT', MEM: 'CT', BNA: 'CT',
  OMA: 'CT', DSM: 'CT', MKE: 'CT', IND: 'CT',
  DEN: 'MT', SLC: 'MT', ABQ: 'MT', TUS: 'MT', ELP: 'MT', BOI: 'MT',
  LAX: 'PT', SFO: 'PT', SJC: 'PT', OAK: 'PT', SEA: 'PT', PDX: 'PT', SAN: 'PT',
  LAS: 'PT', PHX: 'PT', SMF: 'PT', BUR: 'PT', ONT: 'PT', SNA: 'PT',
  HNL: 'HT', ANC: 'AKT', FAI: 'AKT',
};

const AIRPORT_CITY: Record<string, string> = {
  // USA
  JFK: 'New York', LGA: 'New York', EWR: 'Newark', BOS: 'Boston', PHL: 'Philadelphia',
  DCA: 'Washington', IAD: 'Washington', BWI: 'Baltimore', MIA: 'Miami', FLL: 'Fort Lauderdale',
  MCO: 'Orlando', TPA: 'Tampa', ATL: 'Atlanta', CLT: 'Charlotte', RDU: 'Raleigh',
  DTW: 'Detroit', CLE: 'Cleveland', PIT: 'Pittsburgh', ORD: 'Chicago', MDW: 'Chicago',
  MSP: 'Minneapolis', STL: 'St. Louis', MCI: 'Kansas City', MSY: 'New Orleans',
  HOU: 'Houston', IAH: 'Houston', DFW: 'Dallas', DAL: 'Dallas', AUS: 'Austin',
  SAT: 'San Antonio', MEM: 'Memphis', BNA: 'Nashville', DEN: 'Denver', SLC: 'Salt Lake City',
  ABQ: 'Albuquerque', LAX: 'Los Angeles', SFO: 'San Francisco', SJC: 'San Jose',
  OAK: 'Oakland', SEA: 'Seattle', PDX: 'Portland', SAN: 'San Diego', LAS: 'Las Vegas',
  PHX: 'Phoenix', SMF: 'Sacramento', BUR: 'Burbank', HNL: 'Honolulu', ANC: 'Anchorage',
  // International
  LHR: 'London', LGW: 'London', STN: 'London', CDG: 'Paris', ORY: 'Paris',
  FRA: 'Frankfurt', MUC: 'Munich', AMS: 'Amsterdam', MAD: 'Madrid', BCN: 'Barcelona',
  FCO: 'Rome', MXP: 'Milan', LIN: 'Milan', ZRH: 'Zurich', VIE: 'Vienna',
  BRU: 'Brussels', CPH: 'Copenhagen', ARN: 'Stockholm', OSL: 'Oslo', HEL: 'Helsinki',
  DXB: 'Dubai', AUH: 'Abu Dhabi', DOH: 'Doha', IST: 'Istanbul', TLV: 'Tel Aviv',
  BOM: 'Mumbai', DEL: 'Delhi', BLR: 'Bangalore', HYD: 'Hyderabad', MAA: 'Chennai',
  SIN: 'Singapore', KUL: 'Kuala Lumpur', BKK: 'Bangkok', HKG: 'Hong Kong',
  PEK: 'Beijing', PVG: 'Shanghai', CAN: 'Guangzhou', NRT: 'Tokyo', HND: 'Tokyo',
  KIX: 'Osaka', ICN: 'Seoul', SYD: 'Sydney', MEL: 'Melbourne', BNE: 'Brisbane',
  AKL: 'Auckland', YYZ: 'Toronto', YVR: 'Vancouver', YUL: 'Montreal', YYC: 'Calgary',
  GRU: 'São Paulo', GIG: 'Rio de Janeiro', EZE: 'Buenos Aires', BOG: 'Bogotá',
  LIM: 'Lima', SCL: 'Santiago', MEX: 'Mexico City', CUN: 'Cancún', JNB: 'Johannesburg',
  CPT: 'Cape Town', NBO: 'Nairobi', CAI: 'Cairo', CMN: 'Casablanca',
};

function cityName(iata: string): string {
  return AIRPORT_CITY[iata.toUpperCase()] ?? iata;
}

function formatTime(hhmm: string | null, origin?: string): string {
  if (!hhmm) return '--';
  const match = hhmm.match(/(\d{1,2}):(\d{2})/);
  if (!match) return hhmm;
  const h = parseInt(match[1], 10);
  const m = parseInt(match[2], 10);
  const period = h < 12 ? 'AM' : 'PM';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  const mm = m.toString().padStart(2, '0');
  const tz = (origin && AIRPORT_TZ[origin.toUpperCase()]) ? ` ${AIRPORT_TZ[origin.toUpperCase()]}` : '';
  return `${h12}:${mm} ${period}${tz}`;
}

export default function FlightCard({
  flightIata,
  airline,
  origin,
  destination,
  scheduledDeparture,
  currentStatus,
  currentDelayMinutes,
}: Props) {
  const hasRoute = origin && origin !== '???' && destination && destination !== '???';

  return (
    <View style={styles.card}>
      <View style={styles.row}>
        <Text style={styles.flight}>{flightIata}</Text>
        <Text style={styles.airline}>{airline}</Text>
      </View>

      {hasRoute ? (
        <View style={styles.routeRow}>
          <View style={styles.airportCol}>
            <Text style={styles.airport}>{origin}</Text>
            <Text style={styles.city}>{cityName(origin)}</Text>
          </View>
          <Text style={styles.arrow}>→</Text>
          <View style={[styles.airportCol, styles.airportColRight]}>
            <Text style={styles.airport}>{destination}</Text>
            <Text style={[styles.city, styles.cityRight]}>{cityName(destination)}</Text>
          </View>
        </View>
      ) : (
        <Text style={styles.unknownRoute}>Route not provided — showing general risk factors only</Text>
      )}

      <View style={styles.metaRow}>
        <Text style={styles.meta}>Scheduled {formatTime(scheduledDeparture, origin)}</Text>
        {currentStatus ? <Text style={styles.meta}>{currentStatus}</Text> : null}
        {currentDelayMinutes != null && currentDelayMinutes > 0 ? (
          <Text style={[styles.meta, styles.delay]}>+{currentDelayMinutes} min</Text>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  flight: { fontSize: 22, fontWeight: '800', color: '#0f172a' },
  airline: { fontSize: 14, color: '#64748b' },
  routeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 14,
  },
  airportCol: { alignItems: 'flex-start' },
  airportColRight: { alignItems: 'flex-end' },
  airport: { fontSize: 32, fontWeight: '700', color: '#0f172a' },
  city: { fontSize: 12, color: '#64748b', marginTop: 2 },
  cityRight: { textAlign: 'right' },
  arrow: { fontSize: 22, color: '#94a3b8', marginBottom: 14 },
  metaRow: { flexDirection: 'row', gap: 12, marginTop: 14, flexWrap: 'wrap' },
  meta: { fontSize: 13, color: '#475569' },
  delay: { color: '#b91c1c', fontWeight: '700' },
  unknownRoute: { fontSize: 13, color: '#94a3b8', fontStyle: 'italic', marginTop: 8 },
});
