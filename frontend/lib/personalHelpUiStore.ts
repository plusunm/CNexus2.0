import { create } from "zustand";

type PersonalHelpUiState = {
  open: boolean;
  openHelp: () => void;
  closeHelp: () => void;
};

export const usePersonalHelpUiStore = create<PersonalHelpUiState>((set) => ({
  open: false,
  openHelp: () => set({ open: true }),
  closeHelp: () => set({ open: false }),
}));
