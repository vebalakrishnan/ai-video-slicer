import type { ReactNode } from 'react';
import { MotionBox } from '../../lib/motion';

export interface PageWrapperProps {
  children: ReactNode;
}

/**
 * Wrap every page's top-level element in this so it fades/slides in
 * on mount. For animated route transitions on exit too, Phase 2
 * agents should wrap <Routes> in framer-motion's <AnimatePresence
 * mode="wait">.
 */
export function PageWrapper({ children }: PageWrapperProps) {
  return (
    <MotionBox
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ duration: 0.3 }}
      minH="100vh"
    >
      {children}
    </MotionBox>
  );
}
