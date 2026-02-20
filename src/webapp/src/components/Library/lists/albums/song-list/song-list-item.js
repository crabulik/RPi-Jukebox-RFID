import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  IconButton,
  ListItem,
  ListItemButton,
  ListItemText,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';

import { toHHMMSS } from '../../../../../utils/utils';
import request from '../../../../../utils/request';
import MetadataEditor from './MetadataEditor';

const SongListItem = ({
  isSelecting,
  registerMusicToCard,
  song,
}) => {
  const { t } = useTranslation();
  const [editorOpen, setEditorOpen] = useState(false);

  const command = 'play_single';
  const {
    artist,
    duration,
    file,
    title,
  } = song;

  const playSingle = () => {
    request(command, { song_url: file });
  };

  const registerSongToCard = () => (
    registerMusicToCard(command, { song_url: file })
  );

  return (
    <>
      <ListItem
        disablePadding
        secondaryAction={
          !isSelecting && (
            <IconButton
              edge="end"
              size="small"
              aria-label={t('library.metadata-editor.edit-button-label')}
              onClick={(e) => {
                e.stopPropagation();
                setEditorOpen(true);
              }}
            >
              <EditIcon fontSize="small" />
            </IconButton>
          )
        }
      >
        <ListItemButton
          role={undefined}
          onClick={() => (isSelecting ? registerSongToCard() : playSingle())}
        >
          <ListItemText
            primary={title || t('library.albums.unknown-title')}
            secondary={`${artist || t('library.albums.unknown-artist')} • ${toHHMMSS(duration)}`}
          />
        </ListItemButton>
      </ListItem>

      <MetadataEditor
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        song={song}
      />
    </>
  );
};

export default React.memo(SongListItem);
