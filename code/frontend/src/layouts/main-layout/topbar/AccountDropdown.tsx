import {
  Avatar,
  Box,
  Button,
  ListItemIcon,
  Menu,
  MenuItem,
  Stack,
  Typography,
} from '@mui/material';
import { MouseEvent, useState } from 'react';
import Profile from 'assets/Profile.webp';
import IconifyIcon from 'components/base/IconifyIcon';

interface MenuItem {
  id: number;
  label: string;
  icon: string;
}

const menuItems: MenuItem[] = [
  {
    id: 0,
    label: 'Profile',
    icon: 'material-symbols:person',
  },
  {
    id: 1,
    label: 'My Account',
    icon: 'material-symbols:account-box-sharp',
  },
  {
    id: 2,
    label: 'Logout',
    icon: 'uiw:logout',
  },
];

const AccountDropdown = () => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  const handleClick = (event: MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const accountMenuItems = menuItems.map((menuItem) => (
    <MenuItem
      key={menuItem.id}
      onClick={handleClose}
      sx={{
        '&:hover .account-menu-icon': { color: 'common.white' },
      }}
    >
      <ListItemIcon>
        <IconifyIcon
          icon={menuItem.icon}
          sx={{ color: 'primary.main' }}
          className="account-menu-icon"
        />
      </ListItemIcon>
      <Typography variant="body1">{menuItem.label}</Typography>
    </MenuItem>
  ));

  return (
    <>
      <Button
        onClick={handleClick}
        aria-controls={open ? 'account-menu' : undefined}
        aria-haspopup="true"
        aria-expanded={open ? 'true' : undefined}
        sx={{ px: { xs: 1, sm: 2 }, minWidth: 'auto' }}
      >
        <Avatar
          sx={{
            width: { xs: 48, sm: 60 },
            height: { xs: 48, sm: 60 },
            borderRadius: 4,
            mr: { xs: 0, xl: 2.5 },
          }}
          alt="User Profile"
          src={Profile}
        />
        <Box sx={{ display: { xs: 'none', xl: 'block' } }}>
          <Stack direction="row" alignItems="center" columnGap={6}>
            <Typography variant="h6" component="p" color="primary.darker" gutterBottom>
              Musfiq
            </Typography>
            <IconifyIcon icon="ph:caret-down-bold" fontSize={16} color="primary.darker" />
          </Stack>
          <Typography variant="subtitle2" textAlign="left" color="primary.lighter">
            Admin
          </Typography>
        </Box>
      </Button>

      <Menu
        anchorEl={anchorEl}
        id="account-menu"
        open={open}
        onClose={handleClose}
        onClick={handleClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        {accountMenuItems}
      </Menu>
    </>
  );
};

export default AccountDropdown;
