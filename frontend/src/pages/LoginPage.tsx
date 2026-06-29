import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Building2, Loader2 } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const loginSchema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(1, 'La contraseña es requerida'),
})

type LoginFormData = z.infer<typeof loginSchema>

// ---------------------------------------------------------------------------
// OAuth type declarations for the global Google/Apple script objects
// ---------------------------------------------------------------------------

/* eslint-disable @typescript-eslint/no-explicit-any */

declare global {
  interface Window {
    google?: any
    AppleID?: any
  }
}

const GOOGLE_SCRIPT_SRC = 'https://accounts.google.com/gsi/client'
const APPLE_SCRIPT_SRC =
  'https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js'

/**
 * Dynamically load a third-party script exactly once.
 * Returns a promise that resolves with the script element once it has loaded.
 */
function loadScript(src: string): Promise<HTMLScriptElement> {
  return new Promise((resolve, reject) => {
    // Already present in the document — reuse it.
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${src}"]`)
    if (existing) {
      if (existing.dataset.loaded === 'true') {
        resolve(existing)
        return
      }
      existing.addEventListener('load', () => resolve(existing), { once: true })
      existing.addEventListener('error', reject, { once: true })
      return
    }

    const script = document.createElement('script')
    script.src = src
    script.async = true
    script.defer = true
    script.addEventListener('load', () => {
      script.dataset.loaded = 'true'
      resolve(script)
    })
    script.addEventListener('error', reject)
    document.head.appendChild(script)
  })
}

export function LoginPage() {
  const navigate = useNavigate()
  const { login, oauthLogin, isLoading, error, clearError } = useAuth()
  const [showPassword] = useState(false)
  const [oauthError, setOauthError] = useState<string | null>(null)

  // Resolve OAuth client ids from env. These are PUBLIC client ids (safe to expose).
  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined
  const appleClientId = import.meta.env.VITE_APPLE_CLIENT_ID as string | undefined

  const googleButtonRef = useRef<HTMLDivElement>(null)
  const googleInitializedRef = useRef(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  })

  const handleOauthTokens = useCallback(
    async (provider: 'google' | 'apple', idToken: string) => {
      clearError()
      setOauthError(null)
      try {
        await oauthLogin(provider, idToken)
        navigate('/')
      } catch (err) {
        const message =
          err instanceof Error ? err.message : `Error al iniciar sesión con ${provider}`
        setOauthError(message)
      }
    },
    [clearError, oauthLogin, navigate],
  )

  // ---- Google Identity Services ------------------------------------------------
  useEffect(() => {
    if (!googleClientId) return
    let cancelled = false

    loadScript(GOOGLE_SCRIPT_SRC)
      .then(() => {
        if (cancelled || !window.google || googleInitializedRef.current) return
        googleInitializedRef.current = true

        window.google.accounts.id.initialize({
          client_id: googleClientId,
          callback: (response: { credential?: string }) => {
            const credential = response?.credential
            if (credential) {
              handleOauthTokens('google', credential)
            }
          },
        })

        // Render the official Google button into our container.
        if (googleButtonRef.current) {
          window.google.accounts.id.renderButton(googleButtonRef.current, {
            theme: 'outline',
            size: 'large',
            width: '100%',
            text: 'continue_with',
            shape: 'rectangular',
          })
        }
      })
      .catch(() => {
        setOauthError('No se pudo cargar Google Sign-In.')
      })

    return () => {
      cancelled = true
    }
  }, [googleClientId, handleOauthTokens])

  // ---- Apple Sign In with Apple JS --------------------------------------------
  useEffect(() => {
    if (!appleClientId) return
    let cancelled = false

    loadScript(APPLE_SCRIPT_SRC)
      .then(() => {
        if (cancelled || !window.AppleID) return
        window.AppleID.auth.init({
          clientId: appleClientId,
          scope: 'name email',
          redirectURI: window.location.origin + '/login',
          usePopup: true,
        })
      })
      .catch(() => {
        setOauthError('No se pudo cargar Sign in with Apple.')
      })

    return () => {
      cancelled = true
    }
  }, [appleClientId])

  const handleAppleSignIn = useCallback(async () => {
    if (!appleClientId || !window.AppleID) return
    setOauthError(null)
    try {
      const response = await window.AppleID.auth.signIn()
      // Apple returns { authorization: { id_token, code }, user?: {...} }
      const idToken: string | undefined = response?.authorization?.id_token
      if (!idToken) {
        setOauthError('Apple no devolvió un id_token.')
        return
      }
      await handleOauthTokens('apple', idToken)
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Error al iniciar sesión con Apple'
      setOauthError(message)
    }
  }, [appleClientId, handleOauthTokens])

  const onSubmit = async (data: LoginFormData) => {
    clearError()
    try {
      await login(data)
      navigate('/')
    } catch {
      // Error is handled by the auth store
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 to-slate-700 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary">
            <Building2 className="h-6 w-6 text-primary-foreground" />
          </div>
          <CardTitle className="text-2xl">ClínicaSaaS Dental MX</CardTitle>
          <CardDescription>Inicia sesión en tu cuenta</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="doctor@clinica.com"
                {...register('email')}
                disabled={isLoading}
              />
              {errors.email && (
                <p className="text-sm text-destructive">{errors.email.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Contraseña</Label>
              <Input
                id="password"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                {...register('password')}
                disabled={isLoading}
              />
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              )}
            </div>

            {error && (
              <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            )}

            {oauthError && (
              <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                {oauthError}
              </div>
            )}

            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Iniciando sesión...
                </>
              ) : (
                'Iniciar sesión'
              )}
            </Button>

            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground">O continúa con</span>
              </div>
            </div>

            <div className="space-y-3">
              {/* Google */}
              {googleClientId ? (
                <div className="w-full overflow-hidden">
                  <div ref={googleButtonRef} className="flex justify-center [&>div]:w-full" />
                </div>
              ) : (
                <Button
                  type="button"
                  variant="outline"
                  className="w-full"
                  disabled
                  title="No configurado — define VITE_GOOGLE_CLIENT_ID"
                >
                  Google (No configurado)
                </Button>
              )}

              {/* Apple */}
              {appleClientId ? (
                <Button
                  type="button"
                  variant="outline"
                  className="w-full"
                  onClick={handleAppleSignIn}
                  disabled={isLoading}
                >
                  <span className="mr-2"></span>
                  Continuar con Apple
                </Button>
              ) : (
                <Button
                  type="button"
                  variant="outline"
                  className="w-full"
                  disabled
                  title="No configurado — define VITE_APPLE_CLIENT_ID"
                >
                  Apple (No configurado)
                </Button>
              )}
            </div>
          </form>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            ¿No tienes una cuenta?{' '}
            <Link to="/register" className="font-medium text-primary hover:underline">
              Crear cuenta
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}