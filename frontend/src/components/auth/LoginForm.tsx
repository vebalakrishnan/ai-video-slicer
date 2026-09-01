import { useState, type FormEvent } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { isAxiosError } from 'axios';
import { Alert, Stack, Text, chakra } from '@chakra-ui/react';
import { AnimatedInput } from '../ui/AnimatedInput';
import { GradientButton } from '../ui/GradientButton';
import { useAuth } from '../../context/AuthContext';

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const StyledRouterLink = chakra(RouterLink);

interface FormErrors {
  email?: string;
  password?: string;
}

function extractErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    const data: unknown = error.response?.data;
    if (
      data &&
      typeof data === 'object' &&
      'detail' in data &&
      typeof (data as { detail: unknown }).detail === 'string'
    ) {
      return (data as { detail: string }).detail;
    }
  }
  return fallback;
}

/**
 * Credentials-only sign-in form (email + password). Validates required
 * fields and email format client-side, then delegates to
 * `useAuth().login`. No Google/OAuth option — this product is
 * credentials-only.
 */
export function LoginForm() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validate = (): boolean => {
    const nextErrors: FormErrors = {};
    if (!email.trim()) {
      nextErrors.email = 'Email is required';
    } else if (!EMAIL_PATTERN.test(email.trim())) {
      nextErrors.email = 'Enter a valid email address';
    }
    if (!password) {
      nextErrors.password = 'Password is required';
    }
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);

    if (!validate()) {
      return;
    }

    setIsSubmitting(true);
    try {
      await login(email.trim(), password);
      navigate('/dashboard');
    } catch (error) {
      setSubmitError(
        extractErrorMessage(
          error,
          'Invalid email or password. Please try again.',
        ),
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} noValidate>
      <Stack gap={5}>
        <AnimatedInput
          type="email"
          name="email"
          label="Email"
          placeholder="you@example.com"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          error={errors.email}
          autoComplete="email"
        />
        <AnimatedInput
          type="password"
          name="password"
          label="Password"
          placeholder="••••••••"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={errors.password}
          autoComplete="current-password"
        />

        {submitError && (
          <Alert.Root status="error" borderRadius="lg">
            <Alert.Indicator />
            <Alert.Title>{submitError}</Alert.Title>
          </Alert.Root>
        )}

        <GradientButton
          type="submit"
          loading={isSubmitting}
          loadingText="Signing In..."
          w="full"
        >
          Sign In
        </GradientButton>

        <Text fontSize="sm" textAlign="center" color="gray.500">
          Don&apos;t have an account?{' '}
          <StyledRouterLink
            to="/register"
            color="purple.500"
            fontWeight="semibold"
          >
            Create one
          </StyledRouterLink>
        </Text>
      </Stack>
    </form>
  );
}
