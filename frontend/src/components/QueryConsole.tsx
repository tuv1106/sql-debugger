export function QueryConsole() {
  return (
    <main data-testid="query-console" className="h-full flex flex-col overflow-auto">
      <div className="flex-1 p-2">
        <h2 className="text-sm font-semibold text-gray-400">Query Console</h2>
      </div>
      <div data-testid="bottom-drawer" className="border-t border-gray-700 p-2">
        <h2 className="text-sm font-semibold text-gray-400">Results / Lineage</h2>
      </div>
    </main>
  );
}
