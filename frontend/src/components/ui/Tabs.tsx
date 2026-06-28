'use client';

import {
  Tab,
  TabGroup,
  TabList,
  TabPanel,
  TabPanels,
} from '@headlessui/react';

export interface TabItem {
  label: string;
  content: React.ReactNode;
}

interface TabsProps {
  tabs: TabItem[];
  defaultIndex?: number;
  selectedIndex?: number;
  onChange?: (index: number) => void;
}

export function Tabs({ tabs, defaultIndex = 0, selectedIndex, onChange }: TabsProps) {
  const controlled = selectedIndex !== undefined;
  return (
    <TabGroup
      {...(controlled ? { selectedIndex } : { defaultIndex })}
      onChange={onChange}
    >
      <TabList className="flex border-b border-[color:var(--color-border-default)]">
        {tabs.map((tab) => (
          <Tab
            key={tab.label}
            className={({ selected }: { selected: boolean }) =>
              [
                'px-4 py-3 text-sm font-medium border-b-2 -mb-px whitespace-nowrap',
                'transition-colors duration-fast cursor-pointer',
                'focus-visible:outline-2 focus-visible:outline-[var(--color-border-focus)] focus-visible:outline-offset-2',
                selected
                  ? 'text-brand-text border-brand font-semibold'
                  : 'text-secondary border-transparent hover:text-primary',
              ].join(' ')
            }
          >
            {tab.label}
          </Tab>
        ))}
      </TabList>
      <TabPanels>
        {tabs.map((tab) => (
          <TabPanel key={tab.label} className="focus:outline-none">
            {tab.content}
          </TabPanel>
        ))}
      </TabPanels>
    </TabGroup>
  );
}
