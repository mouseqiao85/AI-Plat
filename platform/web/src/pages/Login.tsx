import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Eye, EyeOff, Lock, User, Sparkles, Github, Mail, AlertCircle, CheckCircle } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { authService } from '../services/authApi'
import type { OAuthProvider } from '../types/auth'

function LoginPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login, isAuthenticated, isLoading: storeLoading } = useAuthStore()
  
  const [isLogin, setIsLogin] = useState(true)
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [oauthProviders, setOauthProviders] = useState<OAuthProvider[]>([])
  const [rememberMe, setRememberMe] = useState(false)

  useEffect(() => {
    if (isAuthenticated) {
      const redirectTo = searchParams.get('redirect') || '/'
      navigate(redirectTo, { replace: true })
    }
  }, [isAuthenticated, navigate, searchParams])

  useEffect(() => {
    loadOAuthProviders()
  }, [])

  const loadOAuthProviders = async () => {
    try {
      const providers = await authService.getOAuthProviders()
      setOauthProviders(providers)
    } catch {
      console.log('OAuth providers not available')
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setIsLoading(true)

    try {
      if (isLogin) {
        await login({ username, password })
        setSuccess('登录成功，正在跳转...')
      } else {
        if (password !== confirmPassword) {
          setError('两次输入的密码不一致')
          setIsLoading(false)
          return
        }
        if (password.length < 8) {
          setError('密码长度至少为8位')
          setIsLoading(false)
          return
        }
        await authService.register({
          username,
          email,
          password,
          full_name: fullName || undefined,
        })
        setSuccess('注册成功，请登录')
        setIsLogin(true)
      }
    } catch (err: unknown) {
      const errorMessage = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(errorMessage || (isLogin ? '登录失败，请检查用户名和密码' : '注册失败，请重试'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleOAuthLogin = async (provider: string) => {
    try {
      const authUrl = await authService.getOAuthAuthorizeUrl(provider)
      window.location.href = authUrl
    } catch {
      setError('OAuth登录失败，请重试')
    }
  }

  const getOAuthIcon = (provider: string) => {
    switch (provider) {
      case 'google':
        return <Mail className="w-5 h-5" />
      case 'github':
        return <Github className="w-5 h-5" />
      default:
        return <Sparkles className="w-5 h-5" />
    }
  }

  if (storeLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-accent-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-accent-50">
      <div className="w-full max-w-md">
        <div className="card">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary-500 to-accent-500 rounded-2xl mb-4">
              <Sparkles className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900">NexusMind OS</h1>
            <p className="text-gray-500 mt-2">AI-Plat Platform</p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          {success && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2 text-green-700">
              <CheckCircle className="w-5 h-5 flex-shrink-0" />
              <span className="text-sm">{success}</span>
            </div>
          )}

          <div className="flex mb-6">
            <button
              type="button"
              onClick={() => { setIsLogin(true); setError(''); setSuccess('') }}
              className={`flex-1 py-2 text-center font-medium rounded-l-lg transition-colors ${
                isLogin
                  ? 'bg-primary-50 text-primary-700 border-b-2 border-primary-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              登录
            </button>
            <button
              type="button"
              onClick={() => { setIsLogin(false); setError(''); setSuccess('') }}
              className={`flex-1 py-2 text-center font-medium rounded-r-lg transition-colors ${
                !isLogin
                  ? 'bg-primary-50 text-primary-700 border-b-2 border-primary-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              注册
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                用户名
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="input pl-10 w-full"
                  placeholder="请输入用户名"
                  required
                />
              </div>
            </div>

            {!isLogin && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    邮箱
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="input pl-10 w-full"
                      placeholder="请输入邮箱"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    姓名 (可选)
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="input w-full"
                    placeholder="请输入姓名"
                  />
                </div>
              </>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                密码
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input pl-10 pr-10 w-full"
                  placeholder={isLogin ? "请输入密码" : "密码至少8位"}
                  required
                  minLength={isLogin ? undefined : 8}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                >
                  {showPassword ? (
                    <EyeOff className="w-5 h-5 text-gray-400" />
                  ) : (
                    <Eye className="w-5 h-5 text-gray-400" />
                  )}
                </button>
              </div>
            </div>

            {!isLogin && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  确认密码
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="input pl-10 w-full"
                    placeholder="请再次输入密码"
                    required
                  />
                </div>
              </div>
            )}

            {isLogin && (
              <div className="flex items-center justify-between text-sm">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  <span className="text-gray-600">记住我</span>
                </label>
                <a href="#" className="text-primary-600 hover:text-primary-700">
                  忘记密码?
                </a>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="btn btn-primary w-full py-3"
            >
              {isLoading ? '处理中...' : (isLogin ? '登录' : '注册')}
            </button>
          </form>

          {oauthProviders.length > 0 && (
            <>
              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-white text-gray-500">或使用</span>
                </div>
              </div>

              <div className="space-y-3">
                {oauthProviders.map((provider) => (
                  <button
                    key={provider.name}
                    onClick={() => handleOAuthLogin(provider.name)}
                    className="btn w-full py-3 flex items-center justify-center gap-3 border border-gray-300 bg-white hover:bg-gray-50"
                  >
                    {getOAuthIcon(provider.name)}
                    <span>使用 {provider.display_name} 登录</span>
                  </button>
                ))}
              </div>
            </>
          )}

          <div className="mt-6 text-center text-sm text-gray-500">
            {isLogin ? (
              <>
                还没有账号?{' '}
                <button
                  onClick={() => { setIsLogin(false); setError('') }}
                  className="text-primary-600 hover:text-primary-700 font-medium"
                >
                  立即注册
                </button>
              </>
            ) : (
              <>
                已有账号?{' '}
                <button
                  onClick={() => { setIsLogin(true); setError('') }}
                  className="text-primary-600 hover:text-primary-700 font-medium"
                >
                  立即登录
                </button>
              </>
            )}
          </div>
        </div>

        <p className="text-center text-xs text-gray-400 mt-4">
          © 2025 NexusMind OS. All rights reserved.
        </p>
      </div>
    </div>
  )
}

export default LoginPage
