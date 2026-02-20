import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { findIndex, propEq } from 'ramda';

import {
  CircularProgress,
  Grid,
  FormControl,
  FormControlLabel,
  Radio,
  RadioGroup,
  Typography,
} from '@mui/material';

import request from '../../../utils/request';

const Outputs = () => {
  const { t } = useTranslation();

  const [activeSink, setActiveSink] = useState(null);
  const [sinkList, setSinkList] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);

  const fetchAudioOutputs = async () =>  {
    setIsLoading(true);
    const { result, error } = await request('getAudioOutputs');
    setIsLoading(false);

    if (error || !result) {
      setIsError(true);
      return console.error(error);
    }

    const { active_sink, sink_list } = result;
    const activeSinkIndex = findIndex(
      propEq('pulse_sink_name', active_sink)
    )(sink_list);

    setActiveSink(activeSinkIndex);
    setSinkList(sink_list);
    setIsError(false);
  };

  const setOutput = async (event, sink_index) => {
    const targetIndex = parseInt(sink_index, 10);
    setActiveSink(targetIndex);

    setIsLoading(true);
    const { error } = await request('setAudioOutput', { sink_index: targetIndex });
    if (error) {
      setIsError(true);
      console.error(error);
    }
    await fetchAudioOutputs();
  }

  useEffect(() => {
    fetchAudioOutputs();
    const interval = setInterval(fetchAudioOutputs, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Grid container direction="column">
      <Grid container direction="row" justifyContent="space-between" alignItems="center">
        <Typography>{t('settings.audio.outputs.title')}</Typography>
        {isLoading && <CircularProgress size={20} />}
        {isError && <Typography>⚠️</Typography>}
      </Grid>
      <FormControl component="fieldset">
          <RadioGroup
            aria-label={t('settings.audio.outputs.title')}
            name="audio-outputs"
            value={activeSink}
            onChange={setOutput}
          >
            {sinkList.map(({ alias }, index) =>
              <FormControlLabel
                control={<Radio />}
                label={alias}
                key={index}
                value={index}
              />
            )}
          </RadioGroup>
        </FormControl>
    </Grid>
  );
};

export default Outputs;
