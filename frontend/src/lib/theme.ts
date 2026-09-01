// Chakra UI v3 system config.
//
// Chakra v3 replaces v2's `extendTheme` with `createSystem`. We start
// from `defaultConfig` (Chakra's built-in theme, which already ships
// purple/pink color palettes used across the UI kit for the brand
// gradient) — Phase 2 agents can extend this file with custom tokens,
// semantic tokens, or component recipes as the design evolves.

import { createSystem, defaultConfig } from '@chakra-ui/react';

export const system = createSystem(defaultConfig);
