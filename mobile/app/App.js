import { Buffer } from 'buffer';
global.Buffer = global.Buffer ?? Buffer;

import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar } from 'expo-status-bar';

import { ThemeProvider, useTheme } from './src/context/ThemeContext';

import GameScreen       from './src/screens/GameScreen';
import LeaderboardScreen from './src/screens/LeaderboardScreen';
import HowToPlayScreen  from './src/screens/HowToPlayScreen';
import StrategyScreen   from './src/screens/StrategyScreen';
import SettingsScreen   from './src/screens/SettingsScreen';
import AboutScreen      from './src/screens/AboutScreen';

const Stack = createNativeStackNavigator();

function AppNavigator() {
  const { theme, resolvedScheme } = useTheme();

  const headerStyle = {
    backgroundColor: theme.surface,
  };
  const headerTitleStyle = {
    color: theme.text,
  };

  return (
    <>
      <StatusBar style={resolvedScheme === 'dark' ? 'light' : 'dark'} />
      <NavigationContainer>
        <Stack.Navigator
          initialRouteName="Game"
          screenOptions={{
            headerStyle,
            headerTitleStyle,
            headerTintColor: theme.accent,
            contentStyle: { backgroundColor: theme.background },
          }}
        >
          <Stack.Screen
            name="Game"
            component={GameScreen}
            options={{ title: 'Minesweeper.org' }}
          />
          <Stack.Screen
            name="Leaderboard"
            component={LeaderboardScreen}
            options={{ title: 'Leaderboard' }}
          />
          <Stack.Screen
            name="HowToPlay"
            component={HowToPlayScreen}
            options={{ title: 'How to Play' }}
          />
          <Stack.Screen
            name="Strategy"
            component={StrategyScreen}
            options={{ title: 'Strategy & Tips' }}
          />
          <Stack.Screen
            name="Settings"
            component={SettingsScreen}
            options={{ title: 'Settings' }}
          />
          <Stack.Screen
            name="About"
            component={AboutScreen}
            options={{ title: 'About' }}
          />
        </Stack.Navigator>
      </NavigationContainer>
    </>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AppNavigator />
    </ThemeProvider>
  );
}
