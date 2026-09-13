import { Box, Button, Chip, Paper, Stack, TextField, Typography } from '@mui/material';
import IconifyIcon from 'components/base/IconifyIcon';
import { KeyboardEvent, useState } from 'react';
import {
  PromptResult,
  fetchExampleRequest,
  outcomeLabel,
  sendMessages,
  sendPrompt,
} from 'api/gateway';

const outcomeColor = { cache: 'success', trim: 'info', forward: 'default' } as const;

// Must match the gateway's TOKEN_BUDGET (code/gateway/config.py).
const TRIM_THRESHOLD = 1000;

/** Why a request went through without savings, so "saved 0" never looks like a bug. */
const forwardReason = (baseline: number) =>
  baseline <= TRIM_THRESHOLD
    ? `under ${TRIM_THRESHOLD.toLocaleString()} tokens, too small to be worth trimming`
    : 'no function bodies that could be trimmed';

interface TryItProps {
  onSent?: () => void; // let the page refresh KPIs/feed right away
}

/** Type a prompt → it goes through the gateway → answer + what happened. */
const TryIt = ({ onSent }: TryItProps) => {
  const [prompt, setPrompt] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<PromptResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const send = async () => {
    const msg = prompt.trim();
    if (!msg || busy) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await sendPrompt(msg));
      onSent?.();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  /** Send the realistic example: a task plus 10 project files, like a coding agent. */
  const sendExample = async () => {
    if (busy) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const example = await fetchExampleRequest();
      setResult(await sendMessages(example.messages));
      onSent?.();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      send();
    }
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={0.5}>
        <Typography variant="h4">Try it</Typography>
        <Typography variant="caption" color="text.secondary">
          ⌘/Ctrl + Enter to send
        </Typography>
      </Stack>
      <Typography variant="subtitle1" color="primary.lighter" mb={2}>
        Type a prompt and it goes through the gateway to the model. Ask the same thing twice to see
        a cache hit. The trimmer needs real code over {TRIM_THRESHOLD.toLocaleString()} tokens: use
        the example below, which sends a task plus 10 project files the way a coding agent does.
      </Typography>

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} alignItems="stretch">
        <TextField
          fullWidth
          multiline
          minRows={3}
          placeholder="Ask anything…"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={onKey}
        />
        <Button
          variant="contained"
          onClick={send}
          disabled={busy || !prompt.trim()}
          startIcon={
            <IconifyIcon icon={busy ? 'svg-spinners:ring-resize' : 'solar:plain-2-linear'} />
          }
          sx={{ px: 3, minWidth: 120, alignSelf: { xs: 'stretch', sm: 'stretch' } }}
        >
          {busy ? 'Sending' : 'Send'}
        </Button>
      </Stack>

      <Button
        variant="outlined"
        onClick={sendExample}
        disabled={busy}
        startIcon={<IconifyIcon icon="solar:code-file-linear" />}
        sx={{ mt: 1.5 }}
      >
        Send a real coding request: “fix create_note” + 10 project files
      </Button>

      {busy && (
        <Typography variant="body2" color="text.secondary" mt={2}>
          Thinking… (the first prose request loads the embedding model, ~7 s)
        </Typography>
      )}

      {error && (
        <Typography variant="body2" color="error.main" mt={2}>
          {error}
        </Typography>
      )}

      {result && (
        <Box mt={2.5}>
          {result.last && (
            <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap" mb={1.25}>
              <Chip
                size="small"
                color={outcomeColor[result.last.outcome]}
                label={outcomeLabel[result.last.outcome]}
              />
              <Typography variant="body2" color="text.secondary">
                {result.last.baseline.toLocaleString()} tokens in
              </Typography>
              <Typography variant="body2" color="text.secondary">
                · {result.last.sent.toLocaleString()} sent to model
              </Typography>
              <Typography
                variant="body2"
                color={result.last.saved > 0 ? 'success.main' : 'text.secondary'}
              >
                · saved {result.last.saved.toLocaleString()}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                · {result.ms.toLocaleString()} ms
              </Typography>
            </Stack>
          )}
          {result.last?.outcome === 'forward' && (
            <Typography variant="body2" color="text.secondary" mb={1.25}>
              Forwarded as-is: {forwardReason(result.last.baseline)}.
            </Typography>
          )}
          <Box
            sx={{
              bgcolor: 'grey.100',
              borderRadius: 2,
              p: 2,
              maxHeight: 260,
              overflow: 'auto',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            <Typography variant="body1">{result.answer}</Typography>
          </Box>
        </Box>
      )}
    </Paper>
  );
};

export default TryIt;
