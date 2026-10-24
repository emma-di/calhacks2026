import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import PhoneViewer from "./components/PhoneViewer";
import "./styles.css";
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {new URLSearchParams(location.search).has("viewer") ? (
      <PhoneViewer />
    ) : (
      <App />
    )}
  </React.StrictMode>,
);
