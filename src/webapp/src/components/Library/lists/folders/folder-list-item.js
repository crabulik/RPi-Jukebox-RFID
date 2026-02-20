import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  IconButton,
  ListItem,
  ListItemButton,
  ListItemText,
} from '@mui/material';

import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import EditIcon from '@mui/icons-material/Edit';

import request from '../../../../utils/request';
import FolderLink from './folder-link';
import FolderTypeAvatar from './folder-type-avatar';
import MetadataEditor from '../albums/song-list/MetadataEditor';

const FolderListItem = ({
  folder,
  isSelecting,
  registerMusicToCard,
}) => {
  const { t } = useTranslation();
  const { type, name, relpath } = folder;
  const [editorOpen, setEditorOpen] = useState(false);

  const playItem = () => {
    switch(type) {
      case 'directory': return request('play_folder', { folder: relpath, recursive: true });
      case 'file': return request('play_single', { song_url: relpath });
      // TODO: Add missing Podcast
      // TODO: Add missing Stream
      default: return;
    }
  };

  const registerItemToCard = () => {
    switch(type) {
      case 'directory': return registerMusicToCard('play_folder', { folder: relpath, recursive: true });
      case 'file': return registerMusicToCard('play_single', { song_url: relpath });
      // TODO: Add missing Podcast
      // TODO: Add missing Stream
      default: return;
    }
  };

  // Determine secondary action based on type and mode
  const getSecondaryAction = () => {
    if (type === 'directory') {
      // Directories get the navigate arrow
      return (
        <IconButton
          component={FolderLink}
          data={{ dir: relpath }}
          edge="end"
          aria-label={t('library.folders.show-folder-content')}
        >
          <NavigateNextIcon />
        </IconButton>
      );
    } else if (type === 'file' && !isSelecting) {
      // Files get the edit button (only when not selecting for card registration)
      return (
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
      );
    }
    return undefined;
  };

  return (
    <>
      <ListItem
        disablePadding
        secondaryAction={getSecondaryAction()}
      >
        <ListItemButton onClick={() => (isSelecting ? registerItemToCard() : playItem())}>
          <FolderTypeAvatar type={type} />
          <ListItemText primary={name} />
        </ListItemButton>
      </ListItem>

      {type === 'file' && (
        <MetadataEditor
          open={editorOpen}
          onClose={() => setEditorOpen(false)}
          song={{ file: relpath, title: name }}
        />
      )}
    </>
  );
}

export default FolderListItem;
