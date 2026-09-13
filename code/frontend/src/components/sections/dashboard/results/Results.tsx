import {
  Box,
  Chip,
  Grid,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import { useEffect, useState } from 'react';
import { Benchmarks, fetchBenchmarks } from 'api/gateway';

/**
 * The benchmark results, measured by the gateway itself (GET /benchmarks) with
 * the same code the report and the command line use, so the page can never show
 * a number the code does not produce.
 */
const Results = () => {
  const [b, setB] = useState<Benchmarks | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchBenchmarks()
      .then(setB)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h4" color="primary.dark" mb={0.5}>
        Measured results
      </Typography>
      <Typography variant="subtitle1" color="primary.lighter" mb={2.5}>
        Run live by the gateway with the project's own benchmark code. Every result is checked to
        still be valid code.
      </Typography>

      {error && <Typography color="error.main">{error}</Typography>}
      {!b && !error && <Typography color="text.secondary">Measuring…</Typography>}

      {b && (
        <Grid container spacing={4}>
          {/* ---- trimmer vs baselines ---- */}
          <Grid item xs={12} xl={7}>
            <Typography variant="h6" mb={0.5}>
              Trimmer vs simple baselines
            </Typography>
            <Typography variant="body2" color="text.secondary" mb={1}>
              Task “{b.trimmer.task}” on the {b.trimmer.fixture} fixture (10 files, 45 functions)
            </Typography>
            <Box sx={{ overflow: 'auto' }}>
              <Table size="small" aria-label="trimmer vs baselines">
                <TableHead>
                  <TableRow>
                    <TableCell>Variant</TableCell>
                    <TableCell align="right">Tokens</TableCell>
                    <TableCell align="right">Saved</TableCell>
                    <TableCell>Output</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {b.trimmer.rows.map((r) => {
                    const ours = r.variant.startsWith('trimmer');
                    return (
                      <TableRow
                        key={r.variant}
                        sx={
                          ours
                            ? {
                                bgcolor: (t) => alpha(t.palette.primary.main, 0.08),
                                '& td': { fontWeight: 700 },
                              }
                            : {}
                        }
                      >
                        <TableCell>{r.variant}</TableCell>
                        <TableCell align="right">{r.tokens.toLocaleString()}</TableCell>
                        <TableCell align="right">{r.saved_pct.toFixed(1)}%</TableCell>
                        <TableCell>
                          <Stack direction="row" spacing={1} alignItems="center">
                            <Chip
                              size="small"
                              color={r.valid ? 'success' : 'error'}
                              label={r.valid ? 'valid' : 'broken'}
                            />
                            {r.note && (
                              <Typography variant="caption" color="text.secondary">
                                {r.note}
                              </Typography>
                            )}
                          </Stack>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </Box>
            <Typography variant="caption" color="text.secondary" display="block" mt={1}>
              Reproduce: <code>{b.trimmer.command}</code>
            </Typography>
          </Grid>

          {/* ---- cache curve ---- */}
          <Grid item xs={12} sm={6} xl={2.5}>
            <Typography variant="h6" mb={0.5}>
              Cache savings
            </Typography>
            <Typography variant="body2" color="text.secondary" mb={1}>
              Savings track how often requests repeat
            </Typography>
            <Table size="small" aria-label="cache savings by repeat rate">
              <TableHead>
                <TableRow>
                  <TableCell>Repeats</TableCell>
                  <TableCell align="right">Saved</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {b.cache.points.map((p) => (
                  <TableRow key={p.repeat_rate_pct}>
                    <TableCell>{p.repeat_rate_pct}%</TableCell>
                    <TableCell align="right">{p.reduction_pct.toFixed(1)}%</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Typography variant="caption" color="text.secondary" display="block" mt={1}>
              Reproduce: <code>{b.cache.command}</code>
            </Typography>
          </Grid>

          {/* ---- secrets + latency ---- */}
          <Grid item xs={12} sm={6} xl={2.5}>
            <Typography variant="h6" mb={0.5}>
              Safety and speed
            </Typography>
            <Typography variant="body2" color="text.secondary" mb={1}>
              Secret detection: <b>{b.secrets.missed}</b> of{' '}
              {b.secrets.keys_tested.toLocaleString()} realistic API keys missed
            </Typography>
            <Table size="small" aria-label="cache latency">
              <TableHead>
                <TableRow>
                  <TableCell>Cache latency</TableCell>
                  <TableCell align="right">Added</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {b.latency.rows.map((r) => (
                  <TableRow key={r.case}>
                    <TableCell>{r.case}</TableCell>
                    <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                      {r.latency}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Typography variant="caption" color="text.secondary" display="block" mt={1}>
              Latency {b.latency.note} ({b.latency.source})
            </Typography>
          </Grid>
        </Grid>
      )}
    </Paper>
  );
};

export default Results;
