import { useState } from "react";
import { loginModeus,  searchModeus} from "../../services/api/login";
import { useNavigate } from "react-router-dom"; // Импортируем useNavigate для навигации

const ModeusLoginForm = () => {
  const [email, setEmail] = useState(null);
  const [password, setPassword] = useState(null);
   const [fullName, setFullName] = useState(""); // Строка для поиска
  const [searchResults, setSearchResults] = useState([]); // Результаты поиска
  // const [selectedName, setSelectedName] = useState(""); // Выбранное имя
  const [showSuggestions, setShowSuggestions] = useState(false); // Флаг показа списка
  const [errorMessage, setErrorMessage] = useState(""); // Сообщение об ошибке

  const navigate = useNavigate(); // Инициализируем хук для навигации

  const onClickSearch = async (fullName) => {
    console.log("Поиск ФИО:", fullName);

    let response = await searchModeus(fullName);
    if (response.status !== 200) {
      setErrorMessage("Неверное ФИО. Попробуйте еще раз.");
      return;
    }
    console.log("Результаты поиска:", response.data);
    setSearchResults(response.data);
    setShowSuggestions(true); // Показываем список после поиска
    setErrorMessage(""); // Очищаем ошибку при успешном поиске
  };

    /// Обработчик нажатия клавиши "Enter"
  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      onClickSearch(fullName); // Выполнить поиск, если нажата клавиша Enter
    }
  };

  // Обработчик выбора варианта из списка
  const handleSelect = (name) => {
    setFullName(name); // Устанавливаем выбранное имя
    setShowSuggestions(false); // Скрываем список после выбора
  };

  const onClickLogin = async () => {
    let response = await loginModeus(email, password);

    if (response.status !== 200) {
      setErrorMessage("Неверный логин или пароль. Попробуйте еще раз."); // Устанавливаем текст ошибки
      return;
    }
    console.log(response)
    localStorage.setItem("token", response.data?.token);
    setErrorMessage(""); // Очищаем ошибку при успешном логине

    // Перенаправление на страницу календаря
    navigate("/calendar");
    window.location.reload(); // Обновляем страницу после навигации
  };

  return (
      <div className="login-container">
        <h2>Мое расписание</h2>

        <div className="login-fio">
          <label>Введите ФИО из базы Модеуса</label>

          <div style={{display: "flex", flexDirection: "column"}}>
            <input
                className="input-name"
                id="text"
                type="text"
                placeholder="ФИО для Модеуса"
                value={fullName} // Связано с состоянием fullName
                onChange={(e) => setFullName(e.target.value)} // Обновляем строку поиска
                onKeyPress={handleKeyPress} // Обработчик для нажатия клавиш
            />

            {/* Рендерим выпадающий список или сообщение об отсутствии результатов */}
            {showSuggestions && (
                <ul className="suggestions-list">
                  {searchResults.length > 0 ? (
                      searchResults.map((person, index) => (
                          <li key={index} onClick={() => handleSelect(person.fullName)}>
                            {person.fullName} {/* Отображаем имя */}
                          </li>
                      ))
                  ) : (
                      <li>Нет такого имени</li> // Сообщение, если список пуст
                  )}
                </ul>
            )}
          </div>
        </div>


        <div className="login-netologiya">
          <label>Введите логин и пароль от Нетологии, чтобы увидеть свое расписание</label>
          <div style={{display: "flex", flexDirection: "column"}}>
            <input
                className="input-email"
                id="email"
                type="email"
                placeholder="Логин от Нетологии"
                onChange={(e) => setEmail(e.target.value)}
            />
            <input
                className="input-email"
                id="password"
                type="password"
                placeholder="Пароль от Нетологии"
                onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {/* Сообщение об ошибке */}
          {errorMessage && <p className="error-message">{errorMessage}</p>}

          <button className="login-btn-log" id="login" onClick={onClickLogin}>
            Войти
          </button>
        </div>
      </div>
  );
};

export default ModeusLoginForm;
