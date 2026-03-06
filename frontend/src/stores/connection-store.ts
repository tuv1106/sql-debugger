import { create } from 'zustand';

interface ConnectionState {
  activeConnectionId: string | null;
  setActiveConnectionId: (id: string | null) => void;
}

export const useConnectionStore = create<ConnectionState>((set) => ({
  activeConnectionId: null,
  setActiveConnectionId: (id) => set({ activeConnectionId: id }),
}));
