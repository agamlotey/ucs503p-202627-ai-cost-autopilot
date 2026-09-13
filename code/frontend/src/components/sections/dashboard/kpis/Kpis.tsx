import { Button, Grid, Paper, Stack, Typography } from '@mui/material';
import IconifyIcon from 'components/base/IconifyIcon';
import KpiCard, { KpiItem } from './KpiCard';
import { Stats, resetStats } from 'api/gateway';

const pct = (x: number) => `${(x * 100).toFixed(x > 0 && x < 0.1 ? 1 : 0)}%`;

interface KpisProps {
  stats: Stats;
  online: boolean;
  onReset?: () => void;
}

/** The headline numbers, in the template's stat-card style. */
const Kpis = ({ stats, online, onReset }: KpisProps) => {
  const items: KpiItem[] = [
    {
      label: 'Requests',
      value: stats.requests.toLocaleString(),
      hint: 'through the gateway',
      bgColor: 'error.lighter',
      iconBackgroundColor: 'error.main',
      icon: 'solar:server-linear',
    },
    {
      label: 'Cache hit rate',
      value: pct(stats.hit_rate),
      hint: `${stats.cache_hits.toLocaleString()} served free`,
      bgColor: 'success.lighter',
      iconBackgroundColor: 'success.darker',
      icon: 'solar:bolt-linear',
    },
    {
      label: 'Tokens saved',
      value: stats.saved_tokens.toLocaleString(),
      hint: `of ${stats.baseline_tokens.toLocaleString()} that would be sent`,
      bgColor: 'warning.lighter',
      iconBackgroundColor: 'error.dark',
      icon: 'solar:scissors-linear',
    },
    {
      label: 'Reduction',
      value: pct(stats.reduction),
      hint: `≈ $${stats.saved_usd.toFixed(4)} saved`,
      bgColor: 'secondary.lighter',
      iconBackgroundColor: 'secondary.main',
      icon: 'solar:chart-2-linear',
    },
  ];

  const reset = async () => {
    await resetStats();
    onReset?.();
  };

  return (
    <Paper sx={{ pt: 2.875, pb: 4, px: 4 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={5.375}>
        <div>
          <Typography variant="h4" mb={0.5}>
            Live savings
          </Typography>
          <Typography variant="subtitle1" color={online ? 'primary.lighter' : 'error.main'}>
            {online ? 'polling the gateway every 1.5 s' : 'gateway not reachable — is it running?'}
          </Typography>
        </div>
        <Button
          variant="outlined"
          onClick={reset}
          startIcon={<IconifyIcon icon="solar:restart-linear" />}
        >
          Reset
        </Button>
      </Stack>

      <Grid container spacing={{ xs: 3.875, xl: 2 }} columns={{ xs: 1, sm: 2, md: 4 }}>
        {items.map((item) => (
          <Grid item xs={1} key={item.label}>
            <KpiCard item={item} />
          </Grid>
        ))}
      </Grid>
    </Paper>
  );
};

export default Kpis;
