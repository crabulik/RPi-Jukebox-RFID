import React, { useEffect, useState } from 'react';

import ConnectivityContext from './context';
import { initSockets } from '../../sockets';

const ConnectivityProvider = ({ children }) => {
  const [state, setState] = useState({});

  // Initialize sockets for connectivity context
  useEffect(() => {
    initSockets({
      events: ['host.connectivity'],
      setState,
    });
  }, []);

  const connectivity = state['host.connectivity'] || { wifi: false, bluetooth: false };

  return (
    <ConnectivityContext.Provider value={connectivity}>
      {children}
    </ConnectivityContext.Provider>
  );
};

export default ConnectivityProvider;
