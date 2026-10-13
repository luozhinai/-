import type React from 'react';
import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Drawer } from '../common/Drawer';
import { SidebarNav } from './SidebarNav';
import { ShellHeader } from './ShellHeader';
import { useUiLanguage } from '../../contexts/UiLanguageContext';

type ShellProps = {
  children?: React.ReactNode;
};

export const Shell: React.FC<ShellProps> = ({ children }) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { t } = useUiLanguage();

  useEffect(() => {
    if (!mobileOpen) {
      return undefined;
    }

    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setMobileOpen(false);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [mobileOpen]);

  return (
    <div className="finance-shell min-h-screen bg-background text-foreground">
      <div className="flex min-h-screen w-full">
        <aside
          className="finance-sidebar sticky top-0 z-40 hidden h-screen w-[228px] shrink-0 flex-col border-r border-border bg-card px-3 py-5 lg:flex"
          aria-label={t('layout.desktopSidebar')}
        >
          <SidebarNav onNavigate={() => setMobileOpen(false)} />
        </aside>

        <div className="flex min-h-screen min-w-0 flex-1 flex-col">
          <ShellHeader onOpenMobileNav={() => setMobileOpen(true)} />
          <main className="finance-main min-h-0 min-w-0 flex-1 touch-pan-y">
            {children ?? <Outlet />}
          </main>
        </div>
      </div>

      <Drawer
        isOpen={mobileOpen}
        onClose={() => setMobileOpen(false)}
        title={t('layout.navMenu')}
        width="max-w-xs"
        zIndex={90}
        side="left"
      >
        <SidebarNav onNavigate={() => setMobileOpen(false)} />
      </Drawer>
    </div>
  );
};
