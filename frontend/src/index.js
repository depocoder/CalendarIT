import React from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import reportWebVitals from "./reportWebVitals";
import ReactDOM from "react-dom/client";

import LoginRoute from "./pages/LoginRoute";
import CalendarRoute from "./pages/CalendarRoute";

import "./index.css";
import PrivateRoute from "./components/Calendar/PrivateRoute";

const checkAuth = () => {
  // Проверка наличия токена в localStorage
  return localStorage.getItem("token");
};

const root = ReactDOM.createRoot(document.getElementById("root"));
const router = createBrowserRouter([
    {
     path: "/",
     element: checkAuth() ? <CalendarRoute /> : <LoginRoute />,
    // Если токен есть — перенаправляем на /calendar, если нет — на /login
  },
  {
    path: "/login",
    element: checkAuth() ? <CalendarRoute /> : <LoginRoute />,
      // Перенаправление на календарь, если уже залогинен
  },
  {
    path: "/calendar",
    element: (
      <PrivateRoute>
        <CalendarRoute />
      </PrivateRoute>
    ), // Защищаем страницу календаря
  },
]);

root.render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);

reportWebVitals();
