import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  CircularProgress,
  FormControl,
  Grid,
  NativeSelect,
  Typography,
} from '@mui/material';

import request from '../../../../../utils/request';
import {
  getActionAndCommand,
  getArgsValues,
} from '../../../utils';

const TrustedBluetoothDeviceOptions = ({
  actionData,
  handleActionDataChange,
}) => {
  const { t } = useTranslation();
  const { action, command } = getActionAndCommand(actionData);
  const [deviceAddress] = getArgsValues(actionData);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [devices, setDevices] = useState([]);

  useEffect(() => {
    let isMounted = true;

    const loadTrustedDevices = async () => {
      setIsLoading(true);
      const { result, error } = await request('getTrustedBluetoothDevices');

      if (!isMounted) {
        return;
      }

      if (error) {
        setError(error);
        setDevices([]);
      } else {
        setError(null);
        setDevices(Array.isArray(result) ? result : []);
      }

      setIsLoading(false);
    };

    loadTrustedDevices();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!isLoading && devices.length > 0 && !deviceAddress) {
      handleActionDataChange(action, command, { device_address: devices[0].address });
    }
  }, [
    action,
    command,
    deviceAddress,
    devices,
    handleActionDataChange,
    isLoading,
  ]);

  const onChange = (event) => {
    handleActionDataChange(action, command, { device_address: event.target.value });
  };

  return (
    <Grid container alignItems="center" sx={{ marginTop: '20px' }}>
      <Grid item xs={12}>
        <Typography>
          {t('cards.controls.actions.host.bluetooth.description')}
        </Typography>

        {isLoading && (
          <Grid container sx={{ marginTop: '10px' }}>
            <CircularProgress size={20} />
          </Grid>
        )}

        {!isLoading && error && (
          <Typography color="error" sx={{ marginTop: '10px' }}>
            {t('cards.controls.actions.host.bluetooth.loading-error')}
          </Typography>
        )}

        {!isLoading && !error && devices.length === 0 && (
          <Typography sx={{ marginTop: '10px' }}>
            {t('cards.controls.actions.host.bluetooth.no-devices')}
          </Typography>
        )}

        {!isLoading && !error && devices.length > 0 && (
          <FormControl sx={{ marginTop: '10px', minWidth: '250px' }}>
            <NativeSelect
              value={deviceAddress || devices[0].address}
              onChange={onChange}
              inputProps={{
                'aria-label': t('cards.controls.actions.host.bluetooth.placeholder'),
              }}
            >
              {devices.map((device) => (
                <option key={device.address} value={device.address}>
                  {`${device.name || device.address} (${device.address})${
                    device.connected
                      ? ` ${t('cards.controls.actions.host.bluetooth.connected-suffix')}`
                      : ''
                  }`}
                </option>
              ))}
            </NativeSelect>
          </FormControl>
        )}
      </Grid>
    </Grid>
  );
};

export default TrustedBluetoothDeviceOptions;
