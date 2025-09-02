import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Providers } from './providers'
import {App} from './index'
import Header from "@/components/header";

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Providers>
      <BrowserRouter>
        <Header />
        <div className={"pt-16 h-full"}>
          <App />
        </div>
      </BrowserRouter>
    </Providers>
  </React.StrictMode>
)
