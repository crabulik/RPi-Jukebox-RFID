import React, { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Divider,
  Grid,
  TextField,
  Typography,
} from '@mui/material';

const CARD_WIDTH = 500;
const CARD_HEIGHT = 800;
const IMAGE_SIZE = 500;
const TEXT_AREA_HEIGHT = CARD_HEIGHT - IMAGE_SIZE;
const BORDER_RADIUS = 24;
const BORDER_WIDTH = 6;
const BORDER_COLOR = '#000000';

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

const CardPrint = () => {
  const { t } = useTranslation();
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);

  const [selectedImage, setSelectedImage] = useState(null);
  const [imageElement, setImageElement] = useState(null);
  const [line1, setLine1] = useState('');
  const [line2, setLine2] = useState('');
  const [cardGenerated, setCardGenerated] = useState(false);

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

  const generateCard = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    canvas.width = CARD_WIDTH;
    canvas.height = CARD_HEIGHT;

    // Clip to rounded rect for the whole card
    drawRoundedRect(ctx, 0, 0, CARD_WIDTH, CARD_HEIGHT, BORDER_RADIUS);
    ctx.save();
    ctx.clip();

    // White background
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, CARD_WIDTH, CARD_HEIGHT);

    // Draw image (center-cropped square)
    if (imageElement) {
      centerCropImage(ctx, imageElement, 0, 0, IMAGE_SIZE, IMAGE_SIZE);
    } else {
      ctx.fillStyle = '#e0e0e0';
      ctx.fillRect(0, 0, IMAGE_SIZE, IMAGE_SIZE);
      ctx.fillStyle = '#9e9e9e';
      ctx.font = '28px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(t('settings.cardprint.no_image'), IMAGE_SIZE / 2, IMAGE_SIZE / 2);
    }

    // Text area background
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, IMAGE_SIZE, CARD_WIDTH, TEXT_AREA_HEIGHT);

    const textAreaMidY = IMAGE_SIZE + TEXT_AREA_HEIGHT / 2;

    // Line 1 — bold
    ctx.fillStyle = '#000000';
    ctx.textAlign = 'center';
    ctx.font = `bold 42px sans-serif`;
    ctx.fillText(line1, CARD_WIDTH / 2, textAreaMidY - 30, CARD_WIDTH - 40);

    // Line 2 — normal
    ctx.font = `32px sans-serif`;
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

  const saveCard = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const link = document.createElement('a');
    link.download = 'rfid-card.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
  };

  return (
    <Card>
      <CardHeader title={t('settings.cardprint.title')} />
      <Divider />
      <CardContent>
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
              {selectedImage && (
                <Box
                  component="img"
                  src={selectedImage}
                  alt="selected"
                  sx={{ width: 60, height: 60, objectFit: 'cover', borderRadius: 1, border: '1px solid #ccc' }}
                />
              )}
              {!selectedImage && (
                <Typography variant="body2" color="text.secondary">
                  {t('settings.cardprint.no_image_selected')}
                </Typography>
              )}
            </Box>
          </Grid>

          {/* Text inputs */}
          <Grid item>
            <TextField
              label={t('settings.cardprint.line1')}
              value={line1}
              onChange={(e) => { setLine1(e.target.value); setCardGenerated(false); }}
              fullWidth
              inputProps={{ style: { fontWeight: 'bold' } }}
            />
          </Grid>
          <Grid item>
            <TextField
              label={t('settings.cardprint.line2')}
              value={line2}
              onChange={(e) => { setLine2(e.target.value); setCardGenerated(false); }}
              fullWidth
            />
          </Grid>

          {/* Generate button */}
          <Grid item>
            <Button variant="contained" onClick={generateCard}>
              {t('settings.cardprint.generate')}
            </Button>
          </Grid>
        </Grid>
      </CardContent>

      {/* Preview */}
      {cardGenerated && (
        <>
          <Divider />
          <CardContent>
            <Grid container direction="column" spacing={2} alignItems="center">
              <Grid item>
                <Typography variant="subtitle2" color="text.secondary">
                  {t('settings.cardprint.preview')}
                </Typography>
              </Grid>
              <Grid item>
                <Box sx={{ maxWidth: '100%', overflowX: 'auto' }}>
                  <canvas
                    ref={canvasRef}
                    style={{ display: 'block', maxWidth: '100%', height: 'auto' }}
                  />
                </Box>
              </Grid>
              <Grid item>
                <Button variant="outlined" onClick={saveCard}>
                  {t('settings.cardprint.save')}
                </Button>
              </Grid>
            </Grid>
          </CardContent>
        </>
      )}

      {/* Hidden canvas when not yet generated */}
      {!cardGenerated && (
        <canvas ref={canvasRef} style={{ display: 'none' }} />
      )}
    </Card>
  );
};

export default CardPrint;
