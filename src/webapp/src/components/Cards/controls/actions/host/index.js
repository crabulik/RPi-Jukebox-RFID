import React from 'react';

import CommandSelector from '../../command-selector';
import SayMyIpOptions from './say-my-ip-options';
import TrustedBluetoothDeviceOptions from './trusted-bluetooth-device-options';

import { getActionAndCommand } from '../../../utils';

const SelectHost = ({
  actionData,
  handleActionDataChange,
}) => {
  const { command } = getActionAndCommand(actionData);

  return (
    <>
      <CommandSelector
        actionData={actionData}
        handleActionDataChange={handleActionDataChange}
      />
      {command === 'say_my_ip' &&
        <SayMyIpOptions
          actionData={actionData}
          handleActionDataChange={handleActionDataChange}
        />
      }

      {command === 'connect_trusted_bluetooth_device' &&
        <TrustedBluetoothDeviceOptions
          actionData={actionData}
          handleActionDataChange={handleActionDataChange}
        />
      }
    </>
  );
};

export default SelectHost;
