import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { StatusBar } from 'expo-status-bar';
import { createContext, useContext, useEffect, useRef, useState } from 'react';
import { Platform } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import SearchScreen from './src/screens/SearchScreen';
import ResultScreen from './src/screens/ResultScreen';
import { PredictResponse } from './src/types';

export type RootStackParamList = {
  Search: undefined;
  Result: { prediction: PredictResponse; flightDate: string };
};

// Push token context so any screen can read it
export const PushTokenContext = createContext<string | null>(null);
export function usePushToken() { return useContext(PushTokenContext); }

async function registerForPushNotifications(): Promise<string | null> {
  // Push notifications are native-only — not supported on web
  if (Platform.OS === 'web') return null;

  try {
    const Device = await import('expo-device');
    const Notifications = await import('expo-notifications');

    if (!Device.isDevice) return null;

    Notifications.setNotificationHandler({
      handleNotification: async () => ({
        shouldShowBanner: true,
        shouldShowList: true,
        shouldPlaySound: true,
        shouldSetBadge: false,
      }),
    });

    const { status: existing } = await Notifications.getPermissionsAsync();
    let finalStatus = existing;
    if (existing !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }
    if (finalStatus !== 'granted') return null;

    const token = (await Notifications.getExpoPushTokenAsync()).data;
    return token;
  } catch {
    return null;
  }
}

const Stack = createStackNavigator<RootStackParamList>();

export default function App() {
  const [pushToken, setPushToken] = useState<string | null>(null);

  useEffect(() => {
    registerForPushNotifications().then(setPushToken);
  }, []);

  return (
    <PushTokenContext.Provider value={pushToken}>
      <SafeAreaProvider>
        <NavigationContainer>
          <Stack.Navigator
            screenOptions={{
              headerStyle: { backgroundColor: '#0f172a' },
              headerTintColor: '#fff',
              headerTitleStyle: { fontWeight: '700' },
            }}
          >
            <Stack.Screen name="Search" component={SearchScreen} options={{ title: 'RouteWise' }} />
            <Stack.Screen name="Result" component={ResultScreen} options={{ title: 'Delay Risk' }} />
          </Stack.Navigator>
        </NavigationContainer>
        <StatusBar style="light" />
      </SafeAreaProvider>
    </PushTokenContext.Provider>
  );
}
