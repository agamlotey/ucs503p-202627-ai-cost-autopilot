import { useScrollTrigger } from '@mui/material';
import { cloneElement } from 'react';

interface Props {
  children: React.ReactElement;
}

const ElevationScroll = ({ children }: Props) => {
  const trigger = useScrollTrigger({
    disableHysteresis: true,
    threshold: 0,
  });

  return cloneElement(children, {
    elevation: trigger ? 3 : 0,
  });
};

export default ElevationScroll;
