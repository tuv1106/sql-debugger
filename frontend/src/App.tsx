import { SchemaPanel } from './components/SchemaPanel';
import { QueryConsole } from './components/QueryConsole';
import { AiChatPanel } from './components/AiChatPanel';

export default function App() {
  return (
    <div data-testid="app-layout" className="h-screen w-screen flex bg-gray-900 text-gray-100">
      <div className="w-60 shrink-0">
        <SchemaPanel />
      </div>
      <div className="flex-1 min-w-0">
        <QueryConsole />
      </div>
      <div className="w-80 shrink-0">
        <AiChatPanel />
      </div>
    </div>
  );
}
