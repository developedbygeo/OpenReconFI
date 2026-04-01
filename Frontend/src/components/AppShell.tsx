import {
  AppShell as MantineAppShell,
  NavLink,
  Group,
  Burger,
  useMantineColorScheme,
  ActionIcon,
  Overlay,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import {
  IconDashboard,
  IconFileInvoice,
  IconMailForward,
  IconArrowsExchange,
  IconUpload,
  IconEye,
  IconGitCompare,
  IconLink,
  IconBuildingStore,
  IconReport,
  IconMessageChatbot,
  IconSun,
  IconMoon,
} from '@tabler/icons-react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'

export function AppShell() {
  const location = useLocation()
  const navigate = useNavigate()
  const { colorScheme, toggleColorScheme } = useMantineColorScheme()
  const [opened, { toggle, close }] = useDisclosure()
  const path = location.pathname

  const go = (to: string) => {
    navigate(to)
    close()
  }

  return (
    <MantineAppShell
      navbar={{ width: 240, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      header={{ height: 56 }}
      padding="md"
    >
      <MantineAppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <img
              src="/logo.svg"
              alt="OpenReconFi"
              height={44}
              style={{
                filter: colorScheme === 'dark' ? 'invert(1) hue-rotate(180deg)' : undefined,
                transition: 'filter 200ms',
              }}
            />
          </Group>
          <ActionIcon
            variant="subtle"
            size="lg"
            onClick={toggleColorScheme}
            aria-label="Toggle color scheme"
          >
            {colorScheme === 'dark' ? <IconSun size={20} /> : <IconMoon size={20} />}
          </ActionIcon>
        </Group>
      </MantineAppShell.Header>

      <MantineAppShell.Navbar p="xs" style={{ zIndex: 200 }}>
        <NavLink label="Dashboard" leftSection={<IconDashboard size={20} />} active={path === '/dashboard'} onClick={() => go('/dashboard')} />
        <NavLink label="Invoices" leftSection={<IconFileInvoice size={20} />} active={path.startsWith('/invoices')} onClick={() => go('/invoices')} />
        <NavLink label="Collection" leftSection={<IconMailForward size={20} />} active={path === '/collection'} onClick={() => go('/collection')} />

        <NavLink
          label="Reconciliation"
          leftSection={<IconArrowsExchange size={20} />}
          defaultOpened={path.startsWith('/reconciliation')}
          childrenOffset={28}
        >
          <NavLink label="Upload Statement" leftSection={<IconUpload size={16} />} active={path === '/reconciliation'} onClick={() => go('/reconciliation')} />
          <NavLink label="Overview" leftSection={<IconEye size={16} />} active={path === '/reconciliation/overview'} onClick={() => go('/reconciliation/overview')} />
          <NavLink label="Manual Match" leftSection={<IconLink size={16} />} active={path === '/reconciliation/manual-match'} onClick={() => go('/reconciliation/manual-match')} />
          <NavLink label="Match Review" leftSection={<IconGitCompare size={16} />} active={path === '/reconciliation/matches'} onClick={() => go('/reconciliation/matches')} />
        </NavLink>

        <NavLink label="Vendors" leftSection={<IconBuildingStore size={20} />} active={path.startsWith('/vendors')} onClick={() => go('/vendors')} />
        <NavLink label="Reports" leftSection={<IconReport size={20} />} active={path === '/reports'} onClick={() => go('/reports')} />
        <NavLink label="Chat" leftSection={<IconMessageChatbot size={20} />} active={path === '/chat'} onClick={() => go('/chat')} />
      </MantineAppShell.Navbar>

      {opened && <Overlay onClick={close} zIndex={199} hiddenFrom="sm" />}

      <MantineAppShell.Main>
        <Outlet />
      </MantineAppShell.Main>
    </MantineAppShell>
  )
}
