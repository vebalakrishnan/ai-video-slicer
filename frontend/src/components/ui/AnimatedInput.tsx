import { forwardRef } from 'react';
import type { ComponentProps } from 'react';
import { Field } from '@chakra-ui/react';
import { MotionInput } from '../../lib/motion';

export interface AnimatedInputProps extends ComponentProps<typeof MotionInput> {
  label?: string;
  error?: string;
}

/**
 * Form input with a Chakra Field (label + error text) wrapper and a
 * subtle scale-up on focus. Use for every form input across the app.
 */
export const AnimatedInput = forwardRef<HTMLInputElement, AnimatedInputProps>(
  ({ label, error, ...props }, ref) => (
    <Field.Root invalid={Boolean(error)}>
      {label && <Field.Label>{label}</Field.Label>}
      <MotionInput
        ref={ref}
        whileFocus={{ scale: 1.01 }}
        w="full"
        px={4}
        py={3}
        borderRadius="xl"
        borderWidth="2px"
        borderStyle="solid"
        borderColor={error ? 'red.500' : 'gray.200'}
        outline="none"
        _focus={{ borderColor: error ? 'red.500' : 'purple.500' }}
        {...props}
      />
      {error && <Field.ErrorText>{error}</Field.ErrorText>}
    </Field.Root>
  ),
);

AnimatedInput.displayName = 'AnimatedInput';
