import Background from 'assets/Background.webp';
import LogoPro from 'components/icons/LogoPro';
import { Card, CardContent, Typography, Button, Stack } from '@mui/material';

const NavCard = () => {
  return (
    <Card
      sx={{
        background: `url(${Background}) no-repeat`,
        width: 238,
      }}
    >
      <CardContent sx={{ p: 3 }}>
        <Stack gap={1} alignItems="center" color="common.white">
          <LogoPro sx={{ fontSize: 48 }} />
          <Typography variant="h4">AI Cost Autopilot</Typography>
          <Typography variant="caption" textAlign="center" sx={{ opacity: 0.8 }}>
            A gateway that cuts LLM cost: <br /> cache · trim · autopilot
          </Typography>
          <Button
            variant="contained"
            href="https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot"
            target="_blank"
            rel="noreferrer"
            sx={{
              mt: 3.75,
              px: 5,
              color: 'primary.main',
              bgcolor: 'background.default',
              '&:hover': {
                bgcolor: 'action.hover',
                color: 'common.white',
              },
            }}
          >
            View on GitHub
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default NavCard;
