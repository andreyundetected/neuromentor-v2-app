

    function toggleLanguageDropdown() {
        const dropdown = document.getElementById('lang-dropdown');
        dropdown.style.display = dropdown.style.display === 'flex' ? 'none' : 'flex';
    }

    function selectLanguage(lang) {
        console.log("Selected language:", lang);
        
        fetch(`/set_language/${lang}`, { method: "POST" })
            .then(response => {
                if (response.ok) {
                    location.reload();  // ✅ Перезагрузка страницы
                } else {
                    console.error("Error setting language:", response.statusText);
                }
            })
            .catch(error => console.error("Fetch error:", error));
    }



    function checkInterview(targetUrl) {
        // Проверяем флаг, переданный с бэкенда
        const showInterviewModal = {{ show_interview_modal | tojson }};
        
        if (showInterviewModal) {
            // Показываем модальное окно, если интервью не пройдено
            document.getElementById("interviewModal").style.display = "flex";
        } else {
            // Если интервью пройдено, переходим по URL
            window.location.href = targetUrl;
        }
    }


  
    function stringToColor(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            hash = str.charCodeAt(i) + ((hash << 5) - hash);
        }
        const hue = Math.abs(hash) % 360; // Цветовой тон (0-360 градусов)
        return `hsl(${hue}, 80%, 70%)`; // HSL цвет
    }

    function generateGradient(categories) {
        if (!categories.length) return 'linear-gradient(135deg, #ddd, #bbb)'; // Если нет категорий

        let sortedCategories = categories.map(c => c.trim()).sort(); // Сортируем категории
        let colors = sortedCategories.map(stringToColor); // Преобразуем в цвета

        let gradientParts = colors.map((color, index) => {
            let position = (index / (colors.length - 1)) * 100;
            return `${color} ${position}%`;
        });

        return `linear-gradient(135deg, ${gradientParts.join(', ')})`;
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll(".course-avatar").forEach(el => {
            let categories = el.getAttribute("data-categories").split(",");
            el.style.background = generateGradient(categories);
        });
    });

    function startRecommendation(index) {
        fetch(`/start_recommendation/${index}`, {
            method: 'POST'
        }).then(response => {
            if (response.redirected) {
                window.location.href = response.url;
            }
        });
    }
    let selectedCategories = [];

    // Функция для динамической фильтрации курсов
    function filterCourses() {
    const searchInput = document.getElementById('search-input').value.toLowerCase();
    const courses = document.querySelectorAll('.course-card:not(.add-course-card)');
    
    courses.forEach(course => {
        const courseName = course.querySelector('h2').textContent.toLowerCase();
        let courseCatsText = course.querySelector('.course-categories').textContent.trim(); 
        // Удаляем префикс "Categories:" с учетом возможных пробелов
        courseCatsText = courseCatsText.replace(/^Categories:\s*/i, '');
        const courseCategories = courseCatsText.split(',').map(s => s.trim().toLowerCase());
        
        // Флаг для совпадения по имени
        const nameMatch = courseName.includes(searchInput);
        
        // Флаг для совпадения по выбранным категориям (каждая выбранная категория должна присутствовать)
        let categoryMatch = selectedCategories.every(cat => courseCategories.includes(cat));
        
        if (nameMatch && categoryMatch) {
        course.style.display = 'block';
        } else {
        course.style.display = 'none';
        }
    });
    }

    // Функция переключения категории (множественный выбор)
    function toggleCategory(categoryElement, category) {
      const cat = category.toLowerCase();
      if (selectedCategories.includes(cat)) {
        selectedCategories = selectedCategories.filter(c => c !== cat);
        categoryElement.classList.remove('selected');
      } else {
        selectedCategories.push(cat);
        categoryElement.classList.add('selected');
      }
      filterCourses();
    }

    // Функция сброса выбранных категорий
    function resetCategory() {
      const categoryItems = document.querySelectorAll('.category-item');
      categoryItems.forEach(item => item.classList.remove('selected'));
      selectedCategories = [];
      filterCourses();
    }

    // Извлекаем имя пользователя из мета-тега, переданного сервером
    const username = document.querySelector('meta[name="username"]').getAttribute('content') || 'User';

    // Функция генерации цвета для аватарки на основе имени
    function getUserAvatarColor(name) {
      const colors = ['#FF5733', '#33B5FF', '#FF33F6', '#33FF57', '#FFBD33'];
      let hash = 0;
      for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash);
      }
      const index = Math.abs(hash) % colors.length;
      return colors[index];
    }
    const userAvatarColor = getUserAvatarColor(username);

    // Устанавливаем аватарку в header
    const accountAvatar = document.querySelector('.account-avatar');
    accountAvatar.style.backgroundColor = userAvatarColor;
    accountAvatar.textContent = username.charAt(0).toUpperCase();
  