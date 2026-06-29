import { Jost_400Regular, Jost_500Medium, Jost_600SemiBold, Jost_700Bold, Jost_900Black, useFonts } from '@expo-google-fonts/jost';
import { DarkTheme as NavigationDarkTheme, DefaultTheme as NavigationDefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Stack, usePathname, useRouter } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { MD3DarkTheme, MD3LightTheme, PaperProvider, configureFonts } from 'react-native-paper';
import 'react-native-reanimated';

import { useColorScheme } from '@/hooks/use-color-scheme';
import { AuthProvider, useAuth } from '../providers/AuthProvider';

SplashScreen.preventAutoHideAsync();

export const unstable_settings = {
  anchor: '(tabs)',
};

const baseFont = {
  fontFamily: 'Jost_400Regular',
} as const;

const baseVariants = configureFonts({ config: baseFont });
const customVariants = {
  displayLarge: {
    ...baseVariants.displayLarge,
    fontFamily: 'Jost_400Regular',
  },
  displayMedium: {
    ...baseVariants.displayMedium,
    fontFamily: 'Jost_400Regular',
  },
  displaySmall: {
    ...baseVariants.displaySmall,
    fontFamily: 'Jost_400Regular',
  },
  headlineLarge: {
    ...baseVariants.headlineLarge,
    fontFamily: 'Jost_400Regular',
  },
  headlineMedium: {
    ...baseVariants.headlineMedium,
    fontFamily: 'Jost_400Regular',
  },
  headlineSmall: {
    ...baseVariants.headlineSmall,
    fontFamily: 'Jost_400Regular',
  },
  titleLarge: {
    ...baseVariants.titleLarge,
    fontFamily: 'Jost_500Medium',
  },
  titleMedium: {
    ...baseVariants.titleMedium,
    fontFamily: 'Jost_500Medium',
  },
  titleSmall: {
    ...baseVariants.titleSmall,
    fontFamily: 'Jost_500Medium',
  },
  labelLarge: {
    ...baseVariants.labelLarge,
    fontFamily: 'Jost_500Medium',
  },
  labelMedium: {
    ...baseVariants.labelMedium,
    fontFamily: 'Jost_500Medium',
  },
  labelSmall: {
    ...baseVariants.labelSmall,
    fontFamily: 'Jost_500Medium',
  },
  bodyLarge: {
    ...baseVariants.bodyLarge,
    fontFamily: 'Jost_400Regular',
  },
  bodyMedium: {
    ...baseVariants.bodyMedium,
    fontFamily: 'Jost_400Regular',
  },
  bodySmall: {
    ...baseVariants.bodySmall,
    fontFamily: 'Jost_400Regular',
  },
};
const fonts = configureFonts({
  config: {
    ...baseVariants,
    ...customVariants,
  },
});

export default function RootLayout() {
  const colorScheme = useColorScheme();

  const [loaded, error] = useFonts({
    Jost_400Regular,
    Jost_500Medium,
    Jost_600SemiBold,
    Jost_700Bold,
    Jost_900Black,
  });

  useEffect(() => {
    if (loaded || error) {
      SplashScreen.hideAsync();
    }
  }, [loaded, error]);

  if (!loaded && !error) {
    return null;
  }

  const paperTheme = colorScheme === 'dark'
    ? { ...MD3DarkTheme, fonts: fonts }
    : { ...MD3LightTheme, fonts: fonts };

  return (
    <ThemeProvider value={colorScheme === 'dark' ? NavigationDarkTheme : NavigationDefaultTheme}>
      <PaperProvider theme={paperTheme}>
        <AuthProvider>
          <RootLayoutNav />
        </AuthProvider>
        <StatusBar style="auto" />
      </PaperProvider>
    </ThemeProvider>
  );
}

function RootLayoutNav() {
  const { session, isLoading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;

    const inAuthGroup = pathname === '/login' || pathname === '/signup';
    const isIndex = pathname === '/';

    // Protect all routes except index, login and signup.
    if (!session && !inAuthGroup && !isIndex) {
      router.replace('/login');
    } else if (session && inAuthGroup) {
      // If logged in, redirect away from auth screens
      router.replace('/chat');
    }
  }, [session, isLoading, pathname]);

  return (
    <Stack>
      <Stack.Screen name="index" options={{ headerShown: false, title: 'Welcome' }} />
      <Stack.Screen name="login" options={{ headerShown: false, title: 'Login' }} />
      <Stack.Screen name="signup" options={{ headerShown: false, title: 'Sign Up' }} />
      <Stack.Screen name="chat" options={{ headerShown: true, title: 'Financial Snapshot' }} />
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="modal" options={{ presentation: 'modal', title: 'Modal' }} />
    </Stack>
  );
}
