import { SvgIconProps } from '@mui/material';
import { rootPaths } from './paths';
import DashboardIcon from 'components/icons/DashboardIcon';

export interface MenuItem {
  id: number;
  name: string;
  pathName: string;
  path?: string;
  active?: boolean;
  icon?: string;
  svgIcon?: (props: SvgIconProps) => JSX.Element;
  items?: MenuItem[];
}

const sitemap: MenuItem[] = [
  {
    id: 1,
    name: 'Dashboard',
    path: rootPaths.root,
    pathName: 'dashboard',
    svgIcon: DashboardIcon,
    active: true,
  },
  {
    id: 2,
    name: 'How it works',
    path: 'https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot',
    pathName: 'docs',
    icon: 'ph:book-open',
  },
];

export default sitemap;
