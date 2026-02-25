import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('graphql-ws', () => ({
  createClient: () => ({
    subscribe: () => () => {},
  }),
}));

vi.mock('@/contexts/TriageModeContext', () => ({
  TriageModeProvider: ({ children }) => children,
}));

vi.mock('@/contexts/UserContext', () => ({
  UserProvider: ({ children }) => children,
}));

vi.mock('../components/ThemeProvider', () => ({
  ThemeProvider: ({ children }) => children,
}));

vi.mock('@/components/shared/Tooltip2', () => ({
  default: ({ children }) => children,
}));

vi.mock('@/components/User/UserPromptOverlay', () => ({
  default: () => null,
}));

vi.mock('../components/ThemeToggle', () => ({
  default: ({ isCollapsed }) => <button type="button">{isCollapsed ? 'Theme' : 'Theme Toggle'}</button>,
}));

vi.mock('../components/Dashboard/StatsOverview', () => ({
  default: () => <div data-testid="page-dashboard">Dashboard Page</div>,
}));

vi.mock('../components/FileList/FileList', () => ({
  default: () => <div data-testid="page-files">Files Page</div>,
}));

vi.mock('../components/FileUpload/FileUpload', () => ({
  default: () => <div data-testid="page-upload">Upload Page</div>,
}));

vi.mock('../components/FileViewer/FileViewer', () => ({
  default: () => <div data-testid="page-file-viewer">File Viewer</div>,
}));

vi.mock('../components/Chatbot/ChatbotPage', () => ({
  default: () => <div>Chatbot</div>,
}));

vi.mock('../components/ChromiumDpapi/ChromiumDpapi', () => ({
  default: () => <div>Chromium DPAPI</div>,
}));

vi.mock('../components/Containers/Containers', () => ({
  default: () => <div>Containers</div>,
}));

vi.mock('../components/FileBrowser/FileBrowser', () => ({
  default: () => <div>File Browser</div>,
}));

vi.mock('../components/Findings/FindingsList', () => ({
  default: () => <div>Findings</div>,
}));

vi.mock('../components/Help/HelpPage', () => ({
  default: () => <div>Help</div>,
}));

vi.mock('../components/Reporting/ReportingPage', () => ({
  default: () => <div>Reporting</div>,
}));

vi.mock('../components/Reporting/SourceReportPage', () => ({
  default: () => <div>Source Report</div>,
}));

vi.mock('../components/Reporting/SystemReportPage', () => ({
  default: () => <div>System Report</div>,
}));

vi.mock('../components/Search/DocumentSearch', () => ({
  default: () => <div>Search</div>,
}));

vi.mock('../components/Settings/SettingsPage', () => ({
  default: () => <div>Settings</div>,
}));

vi.mock('../components/Yara/YaraManager', () => ({
  default: () => <div>Yara</div>,
}));

import App from '../App';

describe('app navigation smoke', () => {
  test('navigates through dashboard, upload, and files routes', async () => {
    window.history.pushState({}, '', '/');
    render(<App />);

    expect(screen.getByTestId('page-dashboard')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /file upload/i }));
    await waitFor(() => {
      expect(screen.getByTestId('page-upload')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /^files$/i }));
    await waitFor(() => {
      expect(screen.getByTestId('page-files')).toBeInTheDocument();
    });
  });
});
