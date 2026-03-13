import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';

import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  TextField,
  Typography,
} from '@mui/material';

import request from '../../../../../utils/request';
import CardImageGenerator from '../../../../general/CardImageGenerator';

/**
 * TAG_FIELDS defines which tags are shown in the editor and in what order.
 * Each entry has:
 *   key      – the tag key as used by mutagen (EasyID3 / EasyMP4 etc.)
 *   i18nKey  – key inside translation.json → library.metadata-editor.fields.*
 */
const TAG_FIELDS = [
  { key: 'title',       i18nKey: 'title' },
  { key: 'artist',      i18nKey: 'artist' },
  { key: 'albumartist', i18nKey: 'albumartist' },
  { key: 'album',       i18nKey: 'album' },
  { key: 'tracknumber', i18nKey: 'tracknumber' },
  { key: 'date',        i18nKey: 'date' },
  { key: 'genre',       i18nKey: 'genre' },
  { key: 'comment',     i18nKey: 'comment' },
];

/**
 * MetadataEditor – a dialog that lets the user read and write song tags.
 *
 * Props:
 *   open      {boolean}  – controls dialog visibility
 *   onClose   {function} – called when the dialog should close
 *   song      {object}   – song object with at least { file, title }
 */
const MetadataEditor = ({ open, onClose, song }) => {
  const { t } = useTranslation();

  const [loading, setLoading]   = useState(false);
  const [saving, setSaving]     = useState(false);
  const [error, setError]       = useState(null);
  const [fields, setFields]     = useState({});

  // Load tags when the dialog opens
  useEffect(() => {
    if (!open || !song?.file) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setFields({});

    request('getSongTags', { song_url: song.file })
      .then(({ result, error: err }) => {
        if (cancelled) return;
        if (err || (result && result.error)) {
          setError(err?.message || result?.error || t('library.metadata-editor.load-error'));
        } else {
          // Initialise all TAG_FIELDS so every text field renders (even empty ones)
          const initial = {};
          TAG_FIELDS.forEach(({ key }) => {
            initial[key] = result?.[key] ?? '';
          });
          setFields(initial);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [open, song, t]);

  const handleChange = useCallback((key) => (event) => {
    setFields((prev) => ({ ...prev, [key]: event.target.value }));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);

    const { result, error: err } = await request('setSongTags', {
      song_url: song.file,
      tags: fields,
    });

    setSaving(false);

    if (err || (result && result.error)) {
      setError(err?.message || result?.error || t('library.metadata-editor.save-error'));
    } else {
      onClose();
    }
  };

  const handleClose = () => {
    if (!saving) onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="sm">
      <DialogTitle>
        {t('library.metadata-editor.title', { title: song?.title || song?.file || '' })}
      </DialogTitle>

      <DialogContent dividers>
        {loading && (
          <Box display="flex" justifyContent="center" py={3}>
            <CircularProgress />
          </Box>
        )}

        {!loading && error && (
          <Typography color="error" variant="body2">
            {error}
          </Typography>
        )}

        {!loading && !error && (
          <Box display="flex" flexDirection="column" gap={2} pt={1}>
            {TAG_FIELDS.map(({ key, i18nKey }) => (
              <TextField
                key={key}
                label={t(`library.metadata-editor.fields.${i18nKey}`)}
                value={fields[key] ?? ''}
                onChange={handleChange(key)}
                variant="outlined"
                size="small"
                fullWidth
                disabled={saving}
              />
            ))}
            <Divider />
            <CardImageGenerator
              line1={fields.title ?? ''}
              line2={fields.artist ?? ''}
            />
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose} disabled={saving}>
          {t('general.buttons.cancel')}
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={loading || saving || !!error}
          startIcon={saving ? <CircularProgress size={16} /> : null}
        >
          {t('general.buttons.save')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default MetadataEditor;
