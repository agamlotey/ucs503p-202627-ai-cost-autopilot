import { Card, CardContent, Stack, Typography } from '@mui/material';
import IconifyIcon from 'components/base/IconifyIcon';

export interface KpiItem {
  label: string;
  value: string;
  hint: string;
  bgColor: string;
  iconBackgroundColor: string;
  icon: string;
}

/** Same look as the template's SaleCard, with a free-form hint line. */
const KpiCard = ({ item }: { item: KpiItem }) => {
  const { value, label, hint, bgColor, iconBackgroundColor, icon } = item;
  return (
    <Card sx={{ borderRadius: 4, bgcolor: bgColor }}>
      <CardContent sx={(theme) => ({ p: { xs: `${theme.spacing(2.5)} !important` } })}>
        <Stack
          sx={{
            width: 40,
            height: 40,
            borderRadius: '50%',
            bgcolor: iconBackgroundColor,
            justifyContent: 'center',
            alignItems: 'center',
            mb: 2,
          }}
        >
          <IconifyIcon icon={icon} sx={{ fontSize: 20, color: 'common.white' }} />
        </Stack>
        <Typography variant="h3" color="primary.darker" mb={1}>
          {value}
        </Typography>
        <Typography variant="h6" color="grey.800" component="p" mb={1}>
          {label}
        </Typography>
        <Typography variant="caption" color="text.secondary" component="p">
          {hint}
        </Typography>
      </CardContent>
    </Card>
  );
};

export default KpiCard;
