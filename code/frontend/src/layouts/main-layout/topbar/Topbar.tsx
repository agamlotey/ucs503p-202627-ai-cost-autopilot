import { AppBar, IconButton, Link, Stack, Toolbar, Typography } from '@mui/material';
import { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { rootPaths } from 'routes/paths';
import sitemap from 'routes/sitemap';
import Logo from 'components/icons/Logo';
import IconifyIcon from 'components/base/IconifyIcon';
import ElevationScroll from './ElevationScroll';

interface TopbarProps {
  drawerWidth: number;
  onHandleDrawerToggle: () => void;
}

// The template's search box, language flag, notification bell and stock
// profile photo were decorative placeholders with no function — removed.
const Topbar = ({ drawerWidth, onHandleDrawerToggle }: TopbarProps) => {
  const location = useLocation();

  const pageTitle = useMemo(() => {
    const navItem = sitemap.find((navItem) => location.pathname === navItem.path);
    return navItem?.name ?? 'Dashboard';
  }, [location]);

  return (
    <ElevationScroll>
      <AppBar
        position="fixed"
        sx={{
          width: { lg: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
        }}
      >
        <Toolbar
          sx={{
            justifyContent: 'space-between',
            gap: { xs: 1, sm: 5 },
          }}
        >
          <Stack
            direction="row"
            alignItems="center"
            columnGap={{ xs: 1, sm: 2 }}
            sx={{ display: { lg: 'none' } }}
          >
            <Link href={rootPaths.root}>
              <IconButton color="inherit" aria-label="logo">
                <Logo sx={{ fontSize: 56 }} />
              </IconButton>
            </Link>

            <IconButton color="inherit" aria-label="open drawer" onClick={onHandleDrawerToggle}>
              <IconifyIcon icon="mdi:hamburger-menu" sx={{ fontSize: { xs: 24, sm: 32 } }} />
            </IconButton>
          </Stack>

          <Typography
            variant="h1"
            color="primary.darker"
            sx={{ display: { xs: 'none', lg: 'block' } }}
          >
            {pageTitle}
          </Typography>

          <Typography
            variant="subtitle1"
            color="text.secondary"
            sx={{ display: { xs: 'none', md: 'block' } }}
          >
            AI Cost Autopilot · live savings
          </Typography>
        </Toolbar>
      </AppBar>
    </ElevationScroll>
  );
};

export default Topbar;
