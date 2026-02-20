import React, { useContext } from 'react';
import WifiIcon from '@mui/icons-material/Wifi';
import BluetoothIcon from '@mui/icons-material/Bluetooth';
import Box from '@mui/material/Box';

import ConnectivityContext from '../../context/connectivity/context';

/**
 * StatusBar - displays Wi-Fi and Bluetooth connectivity icons in the top-right corner.
 * Icons only appear when the corresponding interface is active.
 */
const StatusBar = () => {
  const { wifi, bluetooth } = useContext(ConnectivityContext);

  // Debug: log connectivity state
  console.log('StatusBar render:', { wifi, bluetooth });

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 8,
        right: 12,
        display: 'flex',
        gap: 0.5,
        zIndex: 1200,
        backgroundColor: 'rgba(255, 0, 0, 0.1)', // Debug: red tint to see position
      }}
    >
      {wifi && <WifiIcon fontSize="small" color="action" />}
      {bluetooth && <BluetoothIcon fontSize="small" color="action" />}
      {/* Debug: always show at least one icon to verify positioning */}
      {!wifi && !bluetooth && <WifiIcon fontSize="small" sx={{ opacity: 0.3 }} />}
    </Box>
  );
};

export default StatusBar;
