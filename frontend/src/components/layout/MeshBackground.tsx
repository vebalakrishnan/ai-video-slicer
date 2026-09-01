import { Box } from '@chakra-ui/react';
import { MotionBox } from '../../lib/motion';

/**
 * Fixed, full-viewport soft gradient mesh with slowly pulsing blurred
 * blobs. Render once near the root of auth/landing pages, behind the
 * page content (it is position: fixed with a negative z-index and
 * pointer-events: none, so it never intercepts clicks).
 */
export function MeshBackground() {
  return (
    <Box
      position="fixed"
      inset={0}
      zIndex={-1}
      overflow="hidden"
      pointerEvents="none"
    >
      <Box
        position="absolute"
        inset={0}
        bgGradient="to-br"
        gradientFrom="purple.50"
        gradientVia="white"
        gradientTo="pink.50"
        _dark={{
          gradientFrom: 'purple.900',
          gradientVia: 'gray.900',
          gradientTo: 'pink.900',
        }}
      />
      <MotionBox
        position="absolute"
        top={0}
        left="25%"
        w="24rem"
        h="24rem"
        bg="purple.200"
        borderRadius="full"
        filter="blur(80px)"
        animate={{ opacity: [0.2, 0.4, 0.2] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
      />
      <MotionBox
        position="absolute"
        bottom={0}
        right="25%"
        w="24rem"
        h="24rem"
        bg="pink.200"
        borderRadius="full"
        filter="blur(80px)"
        animate={{ opacity: [0.2, 0.4, 0.2] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
      />
    </Box>
  );
}
