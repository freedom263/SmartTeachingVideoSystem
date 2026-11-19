// 通用API调用封装
const API_BASE = '';

// 获取Token
function getToken() {
    return localStorage.getItem('access_token');
}

// 获取当前用户信息
function getCurrentUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
}

// 检查是否已登录
function isLoggedIn() {
    return !!getToken();
}

// 登出
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.href = '/login.html';
}

// API请求封装
async function apiRequest(url, options = {}) {
    const token = getToken();

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
        }
    };

    const finalOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };

    try {
        const response = await fetch(API_BASE + url, finalOptions);
        return response;
    } catch (error) {
        console.error('API请求错误:', error);
        throw error;
    }
}

// 获取用户信息
async function fetchUserInfo() {
    try {
        const response = await apiRequest('/api/auth/me');
        if (response.ok) {
            const user = await response.json();
            localStorage.setItem('user', JSON.stringify(user));
            return user;
        }
    } catch (error) {
        console.error('获取用户信息失败:', error);
    }
    return null;
}

// 初始化导航栏
function initNavbar() {
    const user = getCurrentUser();
    if (!user) return;

    // 更新用户信息显示
    const usernameElement = document.getElementById('navUsername');
    const userAvatarElement = document.getElementById('navUserAvatar');

    if (usernameElement) {
        usernameElement.textContent = user.username;
    }

    if (userAvatarElement) {
        userAvatarElement.textContent = user.username.charAt(0).toUpperCase();
    }

    // 根据角色显示/隐藏管理员菜单
    const adminLink = document.getElementById('adminLink');
    if (adminLink) {
        adminLink.style.display = user.role === 'admin' ? 'block' : 'none';
    }

    // 设置当前页面的active状态
    const currentPath = window.location.pathname;
    document.querySelectorAll('.navbar-menu a').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

// 页面加载时检查登录状态
function checkAuth() {
    if (!isLoggedIn()) {
        // 如果当前不是登录、注册或欢迎页面，跳转到欢迎页
        const currentPath = window.location.pathname;
        if (!currentPath.includes('login.html') &&
            !currentPath.includes('register.html') &&
            !currentPath.includes('welcome.html')) {
            window.location.href = '/';
            return false;
        }
    }
    return true;
}

// 格式化时间
function formatDuration(seconds) {
    if (!seconds) return '0:00';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

// 格式化日期
function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;

    // 小于1分钟
    if (diff < 60000) {
        return '刚刚';
    }
    // 小于1小时
    if (diff < 3600000) {
        return `${Math.floor(diff / 60000)}分钟前`;
    }
    // 小于1天
    if (diff < 86400000) {
        return `${Math.floor(diff / 3600000)}小时前`;
    }
    // 小于7天
    if (diff < 604800000) {
        return `${Math.floor(diff / 86400000)}天前`;
    }

    // 其他情况显示完整日期
    return date.toLocaleDateString('zh-CN');
}

// 显示toast提示
function showToast(message, type = 'info') {
    // 获取或创建toast容器
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        container.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 10000;
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-width: 400px;
        `;
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        padding: 15px 25px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: slideInRight 0.3s ease;
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => {
            toast.remove();
            // 如果容器为空，移除容器
            if (container.children.length === 0) {
                container.remove();
            }
        }, 300);
    }, 3000);
}

// 添加动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// 主题切换功能
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);

    // 更新图标
    const themeIcon = document.getElementById('themeIcon');
    if (themeIcon) {
        themeIcon.textContent = newTheme === 'dark' ? '☀️' : '🌙';
    }
}

// 初始化主题
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);

    const themeIcon = document.getElementById('themeIcon');
    if (themeIcon) {
        themeIcon.textContent = savedTheme === 'dark' ? '☀️' : '🌙';
    }
}

// 页面加载时初始化主题
window.addEventListener('load', initTheme);
