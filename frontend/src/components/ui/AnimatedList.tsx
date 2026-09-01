import type { ReactNode } from 'react';
import { MotionBox } from '../../lib/motion';

export interface AnimatedListProps {
  children: ReactNode[];
}

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

/**
 * Wraps a list of items so they fade/slide in with a staggered delay.
 * Pass an array of ReactNode (e.g. `items.map(item => <Card key={item.id} .../>)`).
 * Use for every list of items across the app.
 */
export function AnimatedList({ children }: AnimatedListProps) {
  return (
    <MotionBox initial="hidden" animate="visible" variants={containerVariants}>
      {children.map((child, index) => (
        // eslint-disable-next-line react/no-array-index-key
        <MotionBox key={index} variants={itemVariants}>
          {child}
        </MotionBox>
      ))}
    </MotionBox>
  );
}
