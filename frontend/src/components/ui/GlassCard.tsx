import type { ComponentProps, ReactNode } from 'react';
import { MotionBox } from '../../lib/motion';

export interface GlassCardProps
  extends Omit<ComponentProps<typeof MotionBox>, 'children'> {
  children: ReactNode;
  className?: string;
}

/**
 * Frosted-glass card container. Fades/slides in on mount and lifts on
 * hover. Use for any card/panel surface across the app.
 */
export function GlassCard({ children, className, ...rest }: GlassCardProps) {
  return (
    <MotionBox
      className={className}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02, y: -5 }}
      p={6}
      borderRadius="2xl"
      bg="whiteAlpha.100"
      backdropFilter="blur(16px)"
      border="1px solid"
      borderColor="whiteAlpha.300"
      boxShadow="xl"
      {...rest}
    >
      {children}
    </MotionBox>
  );
}
