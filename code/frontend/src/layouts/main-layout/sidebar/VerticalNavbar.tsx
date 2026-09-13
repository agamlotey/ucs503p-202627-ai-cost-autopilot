import { Box, Drawer, DrawerProps } from '@mui/material';
import { TransitionEventHandler } from 'react';
import SidebarContent from './SidebarContent';

interface VerticalNavbarProps extends DrawerProps {
  drawerWidth: number;
  mobileOpen: boolean;
  onTransitionEnd?: TransitionEventHandler<HTMLDivElement> | undefined;
  onHandleDrawerClose: () => void;
}

const VerticalNavbar = ({
  drawerWidth,
  mobileOpen,
  onTransitionEnd,
  onHandleDrawerClose,
}: VerticalNavbarProps) => {
  return (
    <Box
      component="nav"
      sx={{ width: { lg: drawerWidth }, flexShrink: { sm: 0 } }}
      aria-label="drawer"
    >
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onTransitionEnd={onTransitionEnd}
        onClose={onHandleDrawerClose}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile.
        }}
        sx={{
          display: { xs: 'block', lg: 'none' },
          '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
        }}
      >
        <SidebarContent />
      </Drawer>

      <Drawer
        variant="permanent"
        sx={{
          display: { xs: 'none', lg: 'block' },
          '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
        }}
        open
      >
        <SidebarContent />
      </Drawer>
    </Box>
  );
};

export default VerticalNavbar;
