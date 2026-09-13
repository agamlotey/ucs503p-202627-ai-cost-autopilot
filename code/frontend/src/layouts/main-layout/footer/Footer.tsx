import { Link, Typography } from '@mui/material';

const Footer = () => {
  return (
    <Typography
      variant="h6"
      component="footer"
      sx={{ pt: 3.75, textAlign: { xs: 'center', md: 'right' } }}
    >
      AI Cost Autopilot · UCS503P 2026–27 · Agam, Devansh, Furmaan ·{' '}
      <Link
        href="https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot"
        target="_blank"
        rel="noopener"
        aria-label="Project repository on GitHub"
        sx={{ color: 'text.primary', '&:hover': { color: 'primary.main' } }}
      >
        GitHub
      </Link>
    </Typography>
  );
};

export default Footer;
