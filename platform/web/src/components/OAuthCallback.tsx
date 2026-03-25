import { useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { CheckCircle, XCircle } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { setTokens } from '../services/authApi'

function OAuthCallback() {
  const { provider } = useParams<{ provider: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { loadUser } = useAuthStore()
  
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [error, setError] = useState('')

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code')
      const state = searchParams.get('state')
      const errorParam = searchParams.get('error')

      if (errorParam) {
        setStatus('error')
        setError(searchParams.get('error_description') || errorParam)
        return
      }

      if (!code || !provider) {
        setStatus('error')
        setError('无效的回调参数')
        return
      }

      try {
        const result = await handleOAuthCallback(provider, code, state || undefined)
        setTokens({
          access_token: result.access_token,
          token_type: result.token_type,
          refresh_token: result.refresh_token,
          expires_in: result.expires_in || 3600,
        })
        
        await loadUser()
        setStatus('success')
        
        setTimeout(() => {
          navigate('/', { replace: true })
        }, 1500)
      } catch (err: unknown) {
        setStatus('error')
        setError((err as Error).message || 'OAuth认证失败')
      }
    }

    handleCallback()
  }, [provider, searchParams, navigate, loadUser])

  const handleOAuthCallback = async (provider: string, code: string, state?: string) => {
    const response = await fetch(`/auth/oauth/callback/${provider}?code=${code}${state ? `&state=${state}` : ''}`, {
      method: 'GET',
      credentials: 'include',
    })
    
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || 'OAuth认证失败')
    }
    
    return response.json()
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-accent-50">
      <div className="card max-w-md w-full text-center">
        {status === 'loading' && (
          <>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              正在处理 {provider?.toUpperCase()} 登录...
            </h2>
            <p className="text-gray-500">请稍候</p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              登录成功!
            </h2>
            <p className="text-gray-500">正在跳转到首页...</p>
          </>
        )}

        {status === 'error' && (
          <>
            <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              登录失败
            </h2>
            <p className="text-red-500 mb-4">{error}</p>
            <button
              onClick={() => navigate('/login')}
              className="btn btn-primary"
            >
              返回登录
            </button>
          </>
        )}
      </div>
    </div>
  )
}

export default OAuthCallback
