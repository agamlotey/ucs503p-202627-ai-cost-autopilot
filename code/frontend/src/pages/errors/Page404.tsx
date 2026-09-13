import { Button, Link, Stack, Typography } from '@mui/material';
import Image from 'components/base/Image';
import errorImg from 'assets/404-page.webp';

const Page404 = () => {
  return (
    <Stack
      alignItems="center"
      justifyContent="center"
      spacing={3}
      sx={{ height: '100vh', px: 5, py: 10 }}
    >
      <Image src={errorImg} sx={{ width: { xs: 1, sm: 1 / 2 }, height: 1 / 2 }} />
      <Button variant="contained" component={Link} href="/">
        <Typography>Go To Dashboard</Typography>
      </Button>
    </Stack>
  );
};

export default Page404;
