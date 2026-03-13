import React, { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  Box,
  Button,
  Grid,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material';

const CARD_WIDTH = 500;
const CARD_HEIGHT = 800;
const IMAGE_SIZE = 500;
const TEXT_AREA_HEIGHT = CARD_HEIGHT - IMAGE_SIZE;
const BORDER_RADIUS = 24;
const BORDER_WIDTH = 6;
const BORDER_COLOR = '#000000';
const BW_CONTRAST_FACTOR = 2.2;

const drawRoundedRect = (ctx, x, y, width, height, radius) => {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
};

const centerCropImage = (ctx, img, destX, destY, destW, destH) => {
  const srcAspect = img.naturalWidth / img.naturalHeight;
  const destAspect = destW / destH;

  let srcX, srcY, srcW, srcH;

  if (srcAspect > destAspect) {
    srcH = img.naturalHeight;
    srcW = srcH * destAspect;
    srcX = (img.naturalWidth - srcW) / 2;
    srcY = 0;
  } else {
    srcW = img.naturalWidth;
    srcH = srcW / destAspect;
    srcX = 0;
    srcY = (img.naturalHeight - srcH) / 2;
  }

  ctx.drawImage(img, srcX, srcY, srcW, srcH, destX, destY, destW, destH);
};

/** Convert the image region of the canvas to high-contrast B/W in place. */
const applyBwFilter = (ctx, x, y, width, height) => {
  const imageData = ctx.getImageData(x, y, width, height);
  const data = imageData.data;

  for (let i = 0; i < data.length; i += 4) {
    // Luminance-weighted grayscale
    const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
    // Contrast boost around midpoint
    const boosted = Math.min(255, Math.max(0, (gray - 128) * BW_CONTRAST_FACTOR + 128));
    data[i] = boosted;
    data[i + 1] = boosted;
    data[i + 2] = boosted;
    // alpha unchanged
  }

  ctx.putImageData(imageData, x, y);
};

/**
 * CardImageGenerator – renders an RFID card image (500×800 px) from an uploaded
 * image and two text lines, then lets the user download the result as PNG or JPEG.
 *
 * Props:
 *   line1  {string}  – bold top text line (e.g. song title)
 *   line2  {string}  – normal bottom text line (e.g. artist)
 */
const CardImageGenerator = ({ line1 = '', line2 = '' }) => {
  const { t } = useTranslation();
  // Single canvas ref — always mounted, visibility toggled via CSS only
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);

  const [selectedImage, setSelectedImage] = useState(null);
  const [imageElement, setImageElement] = useState(null);
  const [cardGenerated, setCardGenerated] = useState(false);
  const [bwMode, setBwMode] = useState(false);

  const handleImageSelect = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        setImageElement(img);
        setSelectedImage(e.target.result);
        setCardGenerated(false);
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  };

  const handleModeChange = (_, newMode) => {
    if (newMode === null) return; // keep at least one selected
    setBwMode(newMode === 'bw');
    setCardGenerated(false);
  };

  const generateCard = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    canvas.width = CARD_WIDTH;
    canvas.height = CARD_HEIGHT;

    // Clip entire card to rounded rect
    drawRoundedRect(ctx, 0, 0, CARD_WIDTH, CARD_HEIGHT, BORDER_RADIUS);
    ctx.save();
    ctx.clip();

    // White background
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, CARD_WIDTH, CARD_HEIGHT);

    // Image area (center-cropped square)
    if (imageElement) {
      centerCropImage(ctx, imageElement, 0, 0, IMAGE_SIZE, IMAGE_SIZE);
      if (bwMode) {
        applyBwFilter(ctx, 0, 0, IMAGE_SIZE, IMAGE_SIZE);
      }
    } else {
      ctx.fillStyle = bwMode ? '#c0c0c0' : '#e0e0e0';
      ctx.fillRect(0, 0, IMAGE_SIZE, IMAGE_SIZE);
      ctx.fillStyle = '#9e9e9e';
      ctx.font = '28px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(t('settings.cardprint.no_image'), IMAGE_SIZE / 2, IMAGE_SIZE / 2);
    }

    // Text area
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, IMAGE_SIZE, CARD_WIDTH, TEXT_AREA_HEIGHT);

    const textAreaMidY = IMAGE_SIZE + TEXT_AREA_HEIGHT / 2;

    ctx.fillStyle = '#000000';
    ctx.textAlign = 'center';

    ctx.font = 'bold 42px sans-serif';
    ctx.fillText(line1, CARD_WIDTH / 2, textAreaMidY - 30, CARD_WIDTH - 40);

    ctx.font = '32px sans-serif';
    ctx.fillText(line2, CARD_WIDTH / 2, textAreaMidY + 40, CARD_WIDTH - 40);

    ctx.restore();

    // Border
    ctx.strokeStyle = BORDER_COLOR;
    ctx.lineWidth = BORDER_WIDTH;
    drawRoundedRect(
      ctx,
      BORDER_WIDTH / 2,
      BORDER_WIDTH / 2,
      CARD_WIDTH - BORDER_WIDTH,
      CARD_HEIGHT - BORDER_WIDTH,
      BORDER_RADIUS
    );
    ctx.stroke();

    setCardGenerated(true);
  };

  const downloadCard = (format) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const link = document.createElement('a');
    if (format === 'jpeg') {
      link.download = 'rfid-card.jpg';
      link.href = canvas.toDataURL('image/jpeg', 0.92);
    } else {
      link.download = 'rfid-card.png';
      link.href = canvas.toDataURL('image/png');
    }
    link.click();
  };

  return (
    <Grid container direction="column" spacing={2}>

      {/* Image picker */}
      <Grid item>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          style={{ display: 'none' }}
          onChange={handleImageSelect}
        />
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button variant="outlined" onClick={() => fileInputRef.current.click()}>
            {t('settings.cardprint.browse')}
          </Button>
          {selectedImage ? (
            <Box
              component="img"
              src={selectedImage}
              alt="selected"
              sx={{ width: 60, height: 60, objectFit: 'cover', borderRadius: 1, border: '1px solid #ccc' }}
            />
          ) : (
            <Typography variant="body2" color="text.secondary">
              {t('settings.cardprint.no_image_selected')}
            </Typography>
          )}
        </Box>
      </Grid>

      {/* Color mode toggle */}
      <Grid item>
        <ToggleButtonGroup
          value={bwMode ? 'bw' : 'color'}
          exclusive
          onChange={handleModeChange}
          size="small"
        >
          <ToggleButton value="color">
            {t('settings.cardprint.mode_color')}
          </ToggleButton>
          <ToggleButton value="bw">
            {t('settings.cardprint.mode_bw')}
          </ToggleButton>
        </ToggleButtonGroup>
      </Grid>

      {/* Generate button */}
      <Grid item>
        <Button variant="contained" onClick={generateCard}>
          {t('settings.cardprint.generate')}
        </Button>
      </Grid>

      {/* Canvas — always mounted, hidden until generated */}
      <Grid item sx={{ display: cardGenerated ? 'block' : 'none' }}>
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          {t('settings.cardprint.preview')}
        </Typography>
        <Box sx={{ maxWidth: '100%', overflowX: 'auto' }}>
          <canvas
            ref={canvasRef}
            style={{ display: 'block', maxWidth: '100%', height: 'auto' }}
          />
        </Box>
        <Box sx={{ mt: 1, display: 'flex', gap: 1 }}>
          <Button variant="outlined" onClick={() => downloadCard('png')}>
            {t('settings.cardprint.save_png')}
          </Button>
          <Button variant="outlined" onClick={() => downloadCard('jpeg')}>
            {t('settings.cardprint.save_jpeg')}
          </Button>
        </Box>
      </Grid>

    </Grid>
  );
};

export default CardImageGenerator;
