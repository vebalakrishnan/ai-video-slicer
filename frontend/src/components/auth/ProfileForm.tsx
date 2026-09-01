import { useState, type FormEvent } from 'react';
import { isAxiosError } from 'axios';
import { Alert, Stack, Text } from '@chakra-ui/react';
import { AnimatedInput } from '../ui/AnimatedInput';
import { GradientButton } from '../ui/GradientButton';
import { useAuth } from '../../context/AuthContext';
import api from '../../services/api';

interface FormErrors {
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
 * Displays the current user's email (read-only) and lets them edit and
 * save their full name via `PUT /auth/me`. AuthContext does not expose
 * a setter for `user`, so on success we show a confirmation and keep
 * the saved value in local state rather than mutating context.
 */
export function ProfileForm() {
  const { user } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name ?? '');
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!user) {
    return null;
  }

  const validate = (): boolean => {
    const nextErrors: FormErrors = {};
    if (!fullName.trim()) {
      nextErrors.fullName = 'Full name is required';
    }
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);
    setSuccessMessage(null);

    if (!validate()) {
      return;
    }

    setIsSubmitting(true);
    try {
      await api.put('/auth/me', { full_name: fullName.trim() });
      setSuccessMessage('Profile updated successfully.');
    } catch (error) {
      setSubmitError(
        extractErrorMessage(
          error,
          'Could not update your profile. Please try again.',
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
          value={user.email}
          readOnly
          disabled
        />
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

        {submitError && (
          <Alert.Root status="error" borderRadius="lg">
            <Alert.Indicator />
            <Alert.Title>{submitError}</Alert.Title>
          </Alert.Root>
        )}

        {successMessage && (
          <Alert.Root status="success" borderRadius="lg">
            <Alert.Indicator />
            <Alert.Title>{successMessage}</Alert.Title>
          </Alert.Root>
        )}

        <GradientButton
          type="submit"
          loading={isSubmitting}
          loadingText="Saving..."
          w="full"
        >
          Save Changes
        </GradientButton>

        <Text fontSize="xs" textAlign="center" color="gray.400">
          Member since {new Date(user.created_at).toLocaleDateString()}
        </Text>
      </Stack>
    </form>
  );
}
