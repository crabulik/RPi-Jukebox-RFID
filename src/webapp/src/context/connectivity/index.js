import React, { useEffect, useState } from 'react';

import ConnectivityContext from './context';
import { initSockets } from '../../sockets';

const ConnectivityProvider = ({ children }) => {
  const [state, setState] = useState({ wifi: false, bluetooth: false });

  // Initialize sockets for connectivity context
  useEffect(() => {
    initSockets({
      events: ['host.connectivity'],
      setState: (newState) => {
        // Extract connectivity data from the 'host.connectivity' topic
        if (newState['host.connectivity']) {
          setState(newState['host.connectivity']);
        }
      },
    });
  }, []);

  return (
    <ConnectivityContext.Provider value={state}>
      {children}
    </ConnectivityContext.Provider>
  );
};

export default ConnectivityProvider;
