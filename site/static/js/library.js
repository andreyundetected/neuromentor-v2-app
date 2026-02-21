document.addEventListener("DOMContentLoaded", () => {
    // 👇 Обработка кнопки языка
    const langBtn = document.getElementById('lang-btn');
    if (langBtn) {
        langBtn.addEventListener('click', () => {
            const dropdown = document.getElementById('lang-dropdown');
            dropdown.style.display = dropdown.style.display === 'flex' ? 'none' : 'flex';
        });
    }

    // 👇 Выбор языка
    document.querySelectorAll('#lang-dropdown button').forEach(btn => {
        btn.addEventListener('click', () => {
            const lang = btn.textContent.trim().toLowerCase();
            fetch(`/set_language/${lang}`, { method: "POST" })
                .then(res => res.ok ? location.reload() : console.error("Error:", res.statusText))
                .catch(err => console.error("Fetch error:", err));
        });
    });

    // 👇 Обработка модалки интервью
    const showInterviewModal = document.querySelector('meta[name="show-interview"]')?.content === 'true';
    window.checkInterview = (targetUrl) => {
        if (showInterviewModal) {
            document.getElementById("interviewModal").style.display = "flex";
        } else {
            window.location.href = targetUrl;
        }
    };

    // 👇 Генерация цветов категорий
    function stringToColor(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            hash = str.charCodeAt(i) + ((hash << 5) - hash);
        }
        const hue = Math.abs(hash) % 360;
        return `hsl(${hue}, 80%, 70%)`;
    }

    function generateGradient(categories) {
        if (!categories.length) return 'linear-gradient(135deg, #ddd, #bbb)';
        let sorted = categories.map(c => c.trim()).sort();
        let colors = sorted.map(stringToColor);
        return `linear-gradient(135deg, ${colors.map((c, i) => `${c} ${(i / (colors.length - 1)) * 100}%`).join(', ')})`;
    }

    // 👇 Градиенты на курсы
    document.querySelectorAll(".course-avatar").forEach(el => {
        let categories = el.getAttribute("data-categories").split(",");
        el.style.background = generateGradient(categories);
    });

    // 👇 Аватарка пользователя
    const username = document.querySelector('meta[name="username"]')?.content || 'User';
    const colors = ['#FF5733', '#33B5FF', '#FF33F6', '#33FF57', '#FFBD33'];
    let hash = 0;
    for (let i = 0; i < username.length; i++) {
        hash = username.charCodeAt(i) + ((hash << 5) - hash);
    }
    const index = Math.abs(hash) % colors.length;
    const accountAvatar = document.querySelector('.account-avatar');
    if (accountAvatar) {
        accountAvatar.style.backgroundColor = colors[index];
        accountAvatar.textContent = username.charAt(0).toUpperCase();
    }

    // 👇 Фильтр по курсам
    let selectedCategories = [];
    function filterCourses() {
        const value = document.getElementById('search-input')?.value.toLowerCase() || '';
        const courses = document.querySelectorAll('.course-card:not(.add-course-card)');
        courses.forEach(course => {
            const name = course.querySelector('h2')?.textContent.toLowerCase() || '';
            let cats = course.querySelector('.course-categories')?.textContent.replace(/^Categories:\s*/i, '').trim() || '';
            let catList = cats.split(',').map(s => s.trim().toLowerCase());
            const nameMatch = name.includes(value);
            const categoryMatch = selectedCategories.every(c => catList.includes(c));
            course.style.display = (nameMatch && categoryMatch) ? 'block' : 'none';
        });
    }

    document.getElementById('search-input')?.addEventListener('input', filterCourses);

    window.toggleCategory = (el, category) => {
        const cat = category.toLowerCase();
        if (selectedCategories.includes(cat)) {
            selectedCategories = selectedCategories.filter(c => c !== cat);
            el.classList.remove('selected');
        } else {
            selectedCategories.push(cat);
            el.classList.add('selected');
        }
        filterCourses();
    };

    window.resetCategory = () => {
        selectedCategories = [];
        document.querySelectorAll('.category-item').forEach(el => el.classList.remove('selected'));
        filterCourses();
    };

    window.startRecommendation = (index) => {
        fetch(`/start_recommendation/${index}`, { method: 'POST' })
            .then(r => r.redirected ? window.location.href = r.url : null);
    };
});
document.querySelectorAll('.category-item').forEach(el => {
    el.addEventListener('click', () => {
        if (el.textContent.trim().toLowerCase() === 'all') {
            resetCategory();
        } else {
            toggleCategory(el, el.textContent);
        }
    });
});
document.querySelector('.add-course-card')?.addEventListener('click', () => {
    checkInterview('/create_course');
});
document.querySelectorAll('.course-card:not(.add-course-card)').forEach((card, index) => {
    card.addEventListener('click', () => {
        checkInterview(`/course/${index}`);
    });
});
