import { ThreadBinding } from "./thread.mjs";
// Add a scenario = add a class here. Each implements: seed · handle · onUserTurn/onLiveTurn · events · interrupt.
export const BINDINGS = { [ThreadBinding.kind]: ThreadBinding };
