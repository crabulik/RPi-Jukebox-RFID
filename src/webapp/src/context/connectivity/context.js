import { createContext } from 'react';

const ConnectivityContext = createContext({
  wifi: false,
  bluetooth: false,
});

export default ConnectivityContext;
