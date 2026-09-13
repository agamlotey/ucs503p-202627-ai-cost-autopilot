import { Link, Stack, SxProps, Typography } from '@mui/material';
import Logo from 'components/icons/Logo';
import { rootPaths } from 'routes/paths';

interface LogoHeaderProps {
  sx?: SxProps;
}
const LogoHeader = (props: LogoHeaderProps) => {
  return (
    <Stack
      direction="row"
      alignItems="center"
      columnGap={3}
      component={Link}
      href={rootPaths.root}
      {...props}
    >
      <Logo sx={{ fontSize: 56 }} />
      <Typography variant="h2" color="primary.darker">
        Autopilot
      </Typography>
    </Stack>
  );
};

export default LogoHeader;
