import { Grid } from '@mui/material';
import useStats from 'hooks/useStats';
import TryIt from 'components/sections/dashboard/try-it/TryIt';
import Kpis from 'components/sections/dashboard/kpis/Kpis';
import TokensChart from 'components/sections/dashboard/tokens-chart/TokensChart';
import Activity from 'components/sections/dashboard/activity/Activity';
import Results from 'components/sections/dashboard/results/Results';

/**
 * AI Cost Autopilot — live savings dashboard.
 * One /stats poll feeds every section; TryIt sends prompts through the gateway
 * and triggers an immediate refresh so the numbers move as you type.
 */
const Dashboard = () => {
  const { stats, online, refresh } = useStats(1500);

  return (
    <Grid container spacing={4}>
      <Grid item xs={12}>
        <TryIt onSent={refresh} />
      </Grid>

      <Grid item xs={12}>
        <Kpis stats={stats} online={online} onReset={refresh} />
      </Grid>

      <Grid item xs={12} xl={5}>
        <TokensChart stats={stats} />
      </Grid>
      <Grid item xs={12} xl={7}>
        <Activity stats={stats} />
      </Grid>

      <Grid item xs={12}>
        <Results />
      </Grid>
    </Grid>
  );
};

export default Dashboard;
