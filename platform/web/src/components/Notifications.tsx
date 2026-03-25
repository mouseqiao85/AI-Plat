import { AlertCircle, CheckCircle, Info, XCircle, X } from 'lucide-react'
import { useAppStore } from '@/stores/appStore'

function Notifications() {
  const { notifications, removeNotification } = useAppStore()

  const getIcon = (type: string) => {
    switch (type) {
      case 'success': return <CheckCircle className="w-5 h-5 text-success-600" />
      case 'error': return <XCircle className="w-5 h-5 text-red-600" />
      case 'info': return <Info className="w-5 h-5 text-primary-600" />
      default: return <AlertCircle className="w-5 h-5 text-yellow-600" />
    }
  }

  const getBgColor = (type: string) => {
    switch (type) {
      case 'success': return 'bg-success-50 border-success-200'
      case 'error': return 'bg-red-50 border-red-200'
      case 'info': return 'bg-primary-50 border-primary-200'
      default: return 'bg-yellow-50 border-yellow-200'
    }
  }

  if (notifications.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2">
      {notifications.map((notification) => (
        <div
          key={notification.id}
          className={`flex items-center gap-3 p-4 rounded-lg border shadow-lg ${getBgColor(notification.type)}`}
        >
          {getIcon(notification.type)}
          <span className="text-gray-700">{notification.message}</span>
          <button
            onClick={() => removeNotification(notification.id)}
            className="p-1 hover:bg-white/50 rounded"
          >
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>
      ))}
    </div>
  )
}

export default Notifications
