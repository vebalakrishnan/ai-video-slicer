// Shared framer-motion + Chakra UI bridge components.
//
// We use framer-motion's `motion.create()` to wrap Chakra UI v3's own
// styled components (Box, Button, Input) rather than wrapping raw
// motion.div/button/input with Chakra's `chakra()` factory. Wrapping
// this direction means framer-motion's prop types (initial, animate,
// whileHover, whileTap, variants, transition, ...) take priority over
// any same-named Chakra style prop (e.g. Chakra's `transition` style
// token), which avoids type conflicts — while Chakra's style props
// (bg, borderRadius, boxShadow, backdropFilter, bgGradient, ...) and
// component recipes (Button/Input styling) are fully preserved.
//
// All UI kit components (GlassCard, GradientButton, AnimatedInput,
// AnimatedList, PageWrapper, MeshBackground) build on these.

import { Box, Button, Input } from '@chakra-ui/react';
import { motion } from 'framer-motion';

export const MotionBox = motion.create(Box);
export const MotionButton = motion.create(Button);
export const MotionInput = motion.create(Input);
