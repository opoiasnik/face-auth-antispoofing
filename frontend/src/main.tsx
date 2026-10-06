import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { configureAuth } from "@/api/http";
import { AuthProvider } from "@/auth/AuthProvider";
import { tokenStorage, UNAUTHORIZED_EVENT } from "@/auth/tokenStorage";

import { App } from "./App";
import "./styles/global.css";

configureAuth(tokenStorage.get, () => window.dispatchEvent(new Event(UNAUTHORIZED_EVENT)));

const root = document.getElementById("root");
if (!root) throw new Error("Root element missing");

createRoot(root).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
