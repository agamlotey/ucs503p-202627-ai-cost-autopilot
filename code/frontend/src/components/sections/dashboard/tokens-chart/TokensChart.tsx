import * as echarts from 'echarts/core';
import {
  TooltipComponent,
  TooltipComponentOption,
  GridComponent,
  GridComponentOption,
  LegendComponent,
  LegendComponentOption,
} from 'echarts/components';
import { BarChart, BarSeriesOption } from 'echarts/charts';
import { CanvasRenderer } from 'echarts/renderers';
import { Paper, Typography, useTheme } from '@mui/material';
import { useMemo } from 'react';
import ReactEchart from 'components/base/ReactEhart';
import { Stats } from 'api/gateway';

echarts.use([TooltipComponent, GridComponent, LegendComponent, BarChart, CanvasRenderer]);

type EChartsOption = echarts.ComposeOption<
  TooltipComponentOption | GridComponentOption | LegendComponentOption | BarSeriesOption
>;

/** Per-request tokens: what would have been sent vs. what actually was (recent first → oldest left). */
const TokensChart = ({ stats }: { stats: Stats }) => {
  const theme = useTheme();

  const option: EChartsOption = useMemo(() => {
    const recent = [...stats.recent].reverse(); // oldest → newest, left → right
    const labels = recent.map((_, i) => `#${stats.requests - recent.length + i + 1}`);
    return {
      color: [theme.palette.grey.A200, theme.palette.success.main],
      tooltip: {
        trigger: 'axis',
        confine: true,
        formatter: (params: unknown) => {
          const p = params as { dataIndex: number }[];
          const r = recent[p[0]?.dataIndex];
          if (!r) return '';
          return (
            `${r.preview || '(no text)'}<br/>` +
            `original ${r.baseline.toLocaleString()} · sent ${r.sent.toLocaleString()} · ` +
            `saved ${r.saved.toLocaleString()} (${r.outcome})`
          );
        },
      },
      legend: {
        data: ['Sent to model', 'Saved'],
        left: 'center',
        bottom: 0,
        icon: 'circle',
        textStyle: { fontFamily: theme.typography.body2.fontFamily },
        itemHeight: 11,
      },
      xAxis: {
        data: labels,
        axisTick: { show: false },
        axisLine: { show: false },
        axisLabel: { fontSize: theme.typography.fontSize - 2, color: theme.palette.grey.A200 },
      },
      yAxis: {
        type: 'value',
        axisLabel: { fontSize: theme.typography.fontSize - 2, color: theme.palette.grey.A200 },
        splitLine: { lineStyle: { color: theme.palette.grey.A400 } },
      },
      grid: { top: '6%', left: 0, right: 6, bottom: 45, containLabel: true },
      series: [
        {
          name: 'Sent to model',
          type: 'bar',
          stack: 'tokens',
          data: recent.map((r) => r.sent),
          itemStyle: { borderRadius: [0, 0, 2, 2] },
          barCategoryGap: '45%',
        },
        {
          name: 'Saved',
          type: 'bar',
          stack: 'tokens',
          data: recent.map((r) => r.saved),
          itemStyle: { borderRadius: [2, 2, 0, 0] },
          barCategoryGap: '45%',
        },
      ],
    };
  }, [theme, stats]);

  return (
    <Paper sx={{ p: 3, height: '100%' }}>
      <Typography variant="h4" mb={0.5}>
        Tokens per request
      </Typography>
      <Typography variant="subtitle1" color="primary.lighter" mb={2}>
        Grey went to the model; green is what the gateway saved
      </Typography>
      {stats.recent.length ? (
        <ReactEchart echarts={echarts} option={option} style={{ height: 247 }} />
      ) : (
        <Typography variant="body2" color="text.secondary" sx={{ py: 8, textAlign: 'center' }}>
          No requests yet — send one above.
        </Typography>
      )}
    </Paper>
  );
};

export default TokensChart;
