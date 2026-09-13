import { Button, ListItemIcon, Menu, MenuItem, Stack, Typography } from '@mui/material';
import { MouseEvent, useState } from 'react';
import IconifyIcon from 'components/base/IconifyIcon';

interface Language {
  id: number;
  code: string;
  lang: string;
  flag: string;
}

const languages: Language[] = [
  {
    id: 0,
    code: 'en-US',
    lang: 'Eng (US)',
    flag: 'circle-flags:us',
  },
  {
    id: 1,
    code: 'eng',
    lang: 'English',
    flag: 'circle-flags:gb-eng',
  },

  {
    id: 2,
    code: 'ban',
    lang: 'বাংলা',
    flag: 'circle-flags:bd',
  },
  {
    id: 3,
    code: 'zh',
    lang: '中文',
    flag: 'circle-flags:cn',
  },
  {
    id: 4,
    code: 'tr',
    lang: 'Türkçe',
    flag: 'circle-flags:tr',
  },
];

const LanguageDropdown = () => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const open = Boolean(anchorEl);

  const handleSelectedLanguage = (event: MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuItemClick = (id: number) => {
    setSelectedIndex(id);
    setAnchorEl(null);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const languageMenuItems = languages?.map((language) => (
    <MenuItem
      key={language.id}
      selected={language.id === selectedIndex}
      onClick={() => handleMenuItemClick(language.id)}
    >
      <ListItemIcon>
        <IconifyIcon icon={language.flag} />
      </ListItemIcon>
      <Typography variant="body1">{language.lang}</Typography>
    </MenuItem>
  ));

  return (
    <div>
      <Button
        onClick={handleSelectedLanguage}
        aria-controls={open ? 'language-dropdown' : undefined}
        aria-haspopup="true"
        aria-expanded={open ? 'true' : undefined}
        sx={{ py: { sm: 2.25 }, px: { xs: 1, sm: 2.25 }, minWidth: { xs: 'auto' } }}
      >
        <IconifyIcon icon={languages[selectedIndex].flag} fontSize={24} />
        <Stack direction="row" alignItems="center" sx={{ display: { xs: 'none', xl: 'flex' } }}>
          <Typography variant="h5" color="grey.600" width={80} mx={2}>
            {languages[selectedIndex].lang}
          </Typography>
          <IconifyIcon icon="ph:caret-down-bold" fontSize={20} color="grey.400" />
        </Stack>
      </Button>

      <Menu
        id="language-dropdown"
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        {languageMenuItems}
      </Menu>
    </div>
  );
};

export default LanguageDropdown;
