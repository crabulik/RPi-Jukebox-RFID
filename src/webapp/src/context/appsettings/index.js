import React, { useEffect, useState } from 'react';

import AppSettingsContext from './context';
import request from '../../utils/request';
import i18n from '../../i18n';

const AppSettingsProvider = ({ children }) => {
  const [settings, setSettings] = useState({});

  useEffect(() => {
    const loadAppSettings = async () => {
      const { result, error } = await request('getAppSettings');
      if(result) {
        setSettings(result);
        if (result.default_language) {
          i18n.changeLanguage(result.default_language);
        }
      }
      if(error) {
        console.error('Error loading AppSettings');
      }
    }

    loadAppSettings();
  }, []);

  const context = {
    setSettings,
    settings,
  };

  return(
    <AppSettingsContext.Provider value={context}>
      { children }
    </AppSettingsContext.Provider>
  )
};

export default AppSettingsProvider;
