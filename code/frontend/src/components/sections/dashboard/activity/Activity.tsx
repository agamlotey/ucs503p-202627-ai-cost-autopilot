import {
  Box,
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { Stats, outcomeLabel } from 'api/gateway';

const outcomeColor = { cache: 'success', trim: 'info', forward: 'default' } as const;

/** Recent requests and what the gateway did with each. */
const Activity = ({ stats }: { stats: Stats }) => {
  return (
    <Paper sx={{ pt: 3, height: '100%' }}>
      <Typography variant="h4" color="primary.dark" px={3} mb={0.5}>
        Recent activity
      </Typography>
      <Typography variant="subtitle1" color="primary.lighter" px={3} mb={1.25}>
        cache hit = served free · trimmed = bulky code collapsed · forwarded = sent as-is
      </Typography>

      <Box sx={{ overflow: 'auto' }}>
        <Table aria-label="recent requests">
          <TableHead>
            <TableRow>
              <TableCell>Time</TableCell>
              <TableCell>Request</TableCell>
              <TableCell>Outcome</TableCell>
              <TableCell align="right">Original</TableCell>
              <TableCell align="right">Sent</TableCell>
              <TableCell align="right">Saved</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {stats.recent.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ color: 'text.secondary', py: 5 }}>
                  No requests yet — send one from the box above, or run <code>python demo.py</code>.
                </TableCell>
              </TableRow>
            )}
            {stats.recent.map((r, i) => (
              <TableRow key={`${r.time}-${i}`}>
                <TableCell sx={{ whiteSpace: 'nowrap' }}>{r.time}</TableCell>
                <TableCell
                  sx={{
                    maxWidth: 380,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                  title={r.preview}
                >
                  {r.preview || <span style={{ opacity: 0.6 }}>(no text)</span>}
                </TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    color={outcomeColor[r.outcome]}
                    label={outcomeLabel[r.outcome]}
                  />
                </TableCell>
                <TableCell align="right">{r.baseline.toLocaleString()}</TableCell>
                <TableCell align="right">{r.sent.toLocaleString()}</TableCell>
                <TableCell
                  align="right"
                  sx={{ color: r.saved > 0 ? 'success.main' : 'text.secondary' }}
                >
                  {r.saved > 0 ? `−${r.saved.toLocaleString()}` : '0'}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    </Paper>
  );
};

export default Activity;
