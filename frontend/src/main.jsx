import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { installStaticApi } from './staticApi'

// 静态部署模式下，把 /api 请求重定向到构建时快照的静态文件（须在渲染前安装）
installStaticApi()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
