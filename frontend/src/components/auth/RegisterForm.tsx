import { useState, type FormEvent } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { isAxiosError } from 'axios';
import { Alert, Stack, Text, chakra } from '@chakra-ui/react';
import { AnimatedInput } from '../ui/AnimatedInput';
import { GradientButton } from '../ui/GradientButton';
import api from '../../services/api';

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 8;

const StyledRouterLink = chakra(RouterLink);

interface FormErrors {
  email?: string;
  password?: string;
  fullName?: string;
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
 * Credentials-only registration form (email + password + full name).
 * Posts directly to `/auth/register` via the shared `api` client (there
 * is no `register` helper on AuthContext), then redirects to `/login`
 * on success. No Google/OAuth option.
 */
export function RegisterForm() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validate = (): boolean => {
    const nextErrors: FormErrors = {};
    if (!fullName.trim()) {
      nextErrors.fullName = 'Full name is required';
    }
    if (!email.trim()) {
      nextErrors.email = 'Email is required';
    } else if (!EMAIL_PATTERN.test(email.trim())) {
      nextErrors.email = 'Enter a valid email address';
    }
    if (!password) {
      nextErrors.password = 'Password is required';
    } else if (password.length < MIN_PASSWORD_LENGTH) {
      nextErrors.password = `Password must be at least ${MIN_PASSWORD_LENGTH} characters`;
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
      await api.post('/auth/register', {
        email: email.trim(),
        password,
        full_name: fullName.trim(),
      });
      void navigate('/login', {
        replace: true,
        state: { registered: true },
      });
    } catch (error) {
      setSubmitError(
        extractErrorMessage(
          error,
          'Could not create your account. Please try again.',
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
          type="text"
          name="fullName"
          label="Full Name"
          placeholder="Jane Doe"
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
          error={errors.fullName}
          autoComplete="name"
        />
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
          autoComplete="new-password"
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
          loadingText="Creating Account..."
          w="full"
        >
          Create Account
        </GradientButton>

        <Text fontSize="sm" textAlign="center" color="gray.500">
          Already have an account?{' '}
          <StyledRouterLink
            to="/login"
            color="purple.500"
            fontWeight="semibold"
          >
            Sign in
          </StyledRouterLink>
        </Text>
      </Stack>
    </form>
  );
}
