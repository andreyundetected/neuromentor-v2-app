const NM = window.NM || { username: 'User', showInterviewModal: false };
const username = NM.username || 'User';
let selectedCategories = [];

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
  if (NM.showInterviewModal) {      // 2
      document.getElementById("interviewModal").style.display = "flex";
  } else {
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

function startRecommendation(index) {
    fetch(`/start_recommendation/${index}`, {
        method: 'POST'
    }).then(response => {
        if (response.redirected) {
            window.location.href = response.url;
        }
    });
}

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

function resetCategory() {
    const categoryItems = document.querySelectorAll('.category-item');
    categoryItems.forEach(item => item.classList.remove('selected'));
    selectedCategories = [];
    filterCourses();
}

function getUserAvatarColor(name) {
    const colors = ['#FF5733', '#33B5FF', '#FF33F6', '#33FF57', '#FFBD33'];
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    const index = Math.abs(hash) % colors.length;
    return colors[index];
}




window.toggleLanguageDropdown = toggleLanguageDropdown;
window.selectLanguage = selectLanguage;
window.checkInterview = checkInterview;
window.filterCourses = filterCourses;
window.toggleCategory = toggleCategory;
window.resetCategory = resetCategory;


const accountAvatar = document.querySelector('.account-avatar');
if (accountAvatar) {
  accountAvatar.style.backgroundColor = getUserAvatarColor(username);
  accountAvatar.textContent = username.charAt(0).toUpperCase();
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.course-avatar').forEach(el => {
    const cats = el.getAttribute('data-categories').split(',');
    el.style.background = generateGradient(cats);
  });
});
