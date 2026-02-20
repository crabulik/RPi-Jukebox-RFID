import { createContext } from 'react';

const AppSettingsContext = createContext({
  showCovers: true,
  default_language: 'en',
});

export default AppSettingsContext;
