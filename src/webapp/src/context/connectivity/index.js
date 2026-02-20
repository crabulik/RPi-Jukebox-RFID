import React, { useEffect, useState } from 'react';

import ConnectivityContext from './context';
import { initSockets } from '../../sockets';

const ConnectivityProvider = ({ children }) => {
  const [connectivity, setConnectivity] = useState({ wifi: false, bluetooth: false });

  // Initialize sockets for connectivity context
  useEffect(() => {
    initSockets({
      events: ['host.connectivity'],
      setState: (newState) => {
        // initSockets passes state like: {'host.connectivity': {wifi: true, bluetooth: false}}
        // Extract the actual connectivity object from the topic key
        if (newState && newState['host.connectivity']) {
          const conn = newState['host.connectivity'];
          setConnectivity({
            wifi: conn.wifi || false,
            bluetooth: conn.bluetooth || false,
          });
        }
      },
    });
  }, []);

  return (
    <ConnectivityContext.Provider value={connectivity}>
      {children}
    </ConnectivityContext.Provider>
  );
};

export default ConnectivityProvider;
