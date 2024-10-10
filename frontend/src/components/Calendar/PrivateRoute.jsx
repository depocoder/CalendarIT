import LoginRoute from "../../pages/LoginRoute";
import React from "react";

const PrivateRoute = ({ children }) => {
  const token = localStorage.getItem("token"); // Проверяем наличие токена

  if (!token) {
    // Если токена нет, перенаправляем на страницу логина
    return <LoginRoute />;
  }

  return children; // Если токен есть, отображаем защищённый компонент
};

export default PrivateRoute;
