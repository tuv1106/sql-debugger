import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import App from './App';

describe('App layout', () => {
  it('renders the 4-panel layout', () => {
    render(<App />);
    expect(screen.getByTestId('app-layout')).toBeInTheDocument();
    expect(screen.getByTestId('schema-panel')).toBeInTheDocument();
    expect(screen.getByTestId('query-console')).toBeInTheDocument();
    expect(screen.getByTestId('bottom-drawer')).toBeInTheDocument();
    expect(screen.getByTestId('ai-chat-panel')).toBeInTheDocument();
  });
});
