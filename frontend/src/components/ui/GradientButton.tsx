import type { ComponentProps, ReactNode } from 'react';
import { MotionButton } from '../../lib/motion';

export interface GradientButtonProps
  extends Omit<ComponentProps<typeof MotionButton>, 'children'> {
  children: ReactNode;
}

/**
 * Primary call-to-action button. Purple -> pink gradient, pill shape,
 * scale+lift on hover, scale-down on tap. Use for every primary
 * action across the app.
 */
export function GradientButton({ children, ...rest }: GradientButtonProps) {
  return (
    <MotionButton
      whileHover={{ scale: 1.02, y: -2 }}
      whileTap={{ scale: 0.98 }}
      px={6}
      py={3}
      borderRadius="full"
      fontWeight="semibold"
      color="white"
      border="none"
      cursor="pointer"
      bgGradient="to-r"
      gradientFrom="purple.500"
      gradientTo="pink.500"
      boxShadow="md"
      _hover={{ boxShadow: 'lg' }}
      _disabled={{ opacity: 0.6, cursor: 'not-allowed' }}
      {...rest}
    >
      {children}
    </MotionButton>
  );
}
