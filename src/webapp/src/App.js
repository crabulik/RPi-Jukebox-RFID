import React, { Suspense } from 'react';

import Grid from '@mui/material/Grid';

import AppSettingsProvider from './context/appsettings';
import ConnectivityProvider from './context/connectivity';
import PubSubProvider from './context/pubsub';
import PlayerProvider from './context/player';
import Router from './router';

function App() {
  return (
    <PubSubProvider>
      <PlayerProvider>
        <ConnectivityProvider>
          <AppSettingsProvider>
            <Grid
              alignItems="center"
              container
              direction="row"
              id="routes"
              justifyContent="center"
            >
              <Router />
            </Grid>
          </AppSettingsProvider>
        </ConnectivityProvider>
      </PlayerProvider>
    </PubSubProvider>
  );
}

// here app catches the suspense from page in case translations are not yet loaded
export default function WrappedApp() {
  return (
    <Suspense fallback="Loading ...">
      <App />
    </Suspense>
  );
}
