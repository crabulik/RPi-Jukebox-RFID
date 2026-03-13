import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  Card,
  CardContent,
  CardHeader,
  Divider,
  Grid,
  TextField,
} from '@mui/material';

import CardImageGenerator from '../../general/CardImageGenerator';

const CardPrint = () => {
  const { t } = useTranslation();
  const [line1, setLine1] = useState('');
  const [line2, setLine2] = useState('');

  return (
    <Card>
      <CardHeader title={t('settings.cardprint.title')} />
      <Divider />
      <CardContent>
        <Grid container direction="column" spacing={2}>
          <Grid item>
            <TextField
              label={t('settings.cardprint.line1')}
              value={line1}
              onChange={(e) => setLine1(e.target.value)}
              fullWidth
              inputProps={{ style: { fontWeight: 'bold' } }}
            />
          </Grid>
          <Grid item>
            <TextField
              label={t('settings.cardprint.line2')}
              value={line2}
              onChange={(e) => setLine2(e.target.value)}
              fullWidth
            />
          </Grid>
          <Grid item>
            <CardImageGenerator line1={line1} line2={line2} />
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default CardPrint;
