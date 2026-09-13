import { Box, List, Stack, Toolbar } from '@mui/material';
import sitemap from 'routes/sitemap';
import LogoHeader from './LogoHeader';
import NavCard from './NavCard';
import NavItem from './NavItem';

const NavItems = () => {
  return (
    <List
      sx={{
        display: 'inline-flex',
        flexDirection: 'column',
        gap: 3,
      }}
    >
      {sitemap.map((navItem) => (
        <NavItem key={navItem.id} item={navItem} />
      ))}
    </List>
  );
};

const SidebarContent = () => {
  return (
    <>
      <Toolbar disableGutters>
        <LogoHeader />
      </Toolbar>

      <Box
        sx={(theme) => ({
          px: 5,
          height: `calc(100vh - ${theme.mixins.toolbar.minHeight}px)`,
          overflowY: 'auto',
        })}
      >
        <Stack gap={17} py={4}>
          <NavItems />
          <NavCard />
        </Stack>
      </Box>
    </>
  );
};

export default SidebarContent;
