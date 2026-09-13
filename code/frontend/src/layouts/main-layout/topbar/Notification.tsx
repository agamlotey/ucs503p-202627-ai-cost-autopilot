import { Badge, Button } from '@mui/material';
import IconifyIcon from 'components/base/IconifyIcon';

const Notification = () => {
  return (
    <Button
      aria-label="notifications"
      sx={{
        bgcolor: 'warning.light',
        p: { xs: 1, sm: 1.5 },
        minWidth: 'auto',
      }}
    >
      <Badge badgeContent=" " variant="dot">
        <IconifyIcon
          icon="clarity:notification-line"
          sx={{ fontSize: 24, color: 'warning.main' }}
        />
      </Badge>
    </Button>
  );
};

export default Notification;
