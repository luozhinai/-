import type React from 'react';
import { Menu } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import type { UiTextKey } from '../../i18n/uiText';
import { UiLanguageToggle } from '../i18n/UiLanguageToggle';
import { ThemeToggle } from '../theme/ThemeToggle';
import { DesktopUpdateIndicator } from './DesktopUpdateIndicator';

type ShellHeaderProps = {
  onOpenMobileNav: () => void;
};

const TITLES: Record<string, { title: UiTextKey; description: UiTextKey }> = {
  '/': { title: 'layout.route.home.title', description: 'layout.route.home.description' },
  '/chat': { title: 'layout.route.chat.title', description: 'layout.route.chat.description' },
  '/portfolio': { title: 'layout.route.portfolio.title', description: 'layout.route.portfolio.description' },
  '/decision-signals': { title: 'layout.nav.decisionSignals', description: 'layout.route.home.description' },
  '/screening': { title: 'layout.route.screening.title', description: 'layout.route.screening.description' },
  '/backtest': { title: 'layout.route.backtest.title', description: 'layout.route.backtest.description' },
  '/alerts': { title: 'layout.route.alerts.title', description: 'layout.route.alerts.description' },
  '/usage': { title: 'layout.route.usage.title', description: 'layout.route.usage.description' },
  '/settings': { title: 'layout.route.settings.title', description: 'layout.route.settings.description' },
};

export const ShellHeader: React.FC<ShellHeaderProps> = ({
  onOpenMobileNav,
}) => {
  const location = useLocation();
  const { t } = useUiLanguage();
  const current = TITLES[location.pathname];

  return (
    <header className="finance-header sticky top-0 z-30 border-b border-border bg-card">
      <div className="flex h-[68px] w-full items-center gap-3 px-4 sm:px-6 lg:px-8">
        <button
          type="button"
          onClick={onOpenMobileNav}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-card text-secondary-text transition-colors hover:bg-hover hover:text-foreground lg:hidden"
          aria-label={t('layout.openNav')}
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="min-w-0 flex-1">
          <p className="truncate text-[15px] font-semibold text-foreground">{current ? t(current.title) : t('layout.appFallbackTitle')}</p>
          <p className="hidden truncate text-[11px] text-secondary-text sm:block">{current ? t(current.description) : t('layout.appFallbackDescription')}</p>
        </div>

        <DesktopUpdateIndicator />
        <UiLanguageToggle />
        <ThemeToggle />
      </div>
    </header>
  );
};
