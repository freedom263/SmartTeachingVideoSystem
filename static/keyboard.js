/**
 * 键盘快捷键管理器
 * 为教师用户提供便捷的键盘操作
 */

class KeyboardShortcuts {
    constructor() {
        this.shortcuts = {
            // 导航快捷键
            'ctrl+h': () => this.navigate('/index.html'),
            'ctrl+u': () => this.navigate('/upload.html'),
            'ctrl+t': () => this.navigate('/tasks.html'),
            'ctrl+p': () => this.navigate('/profile.html'),

            // 功能快捷键
            'escape': () => this.closeModals(),
            'ctrl+k': () => this.toggleKeyboardHints(),
            '?': () => this.toggleKeyboardHints(),

            // 主题切换
            'ctrl+shift+d': () => this.toggleTheme()
        };

        this.init();
    }

    init() {
        document.addEventListener('keydown', (e) => {
            const key = this.getKeyCombo(e);

            if (this.shortcuts[key]) {
                e.preventDefault();
                this.shortcuts[key]();
            }
        });
    }

    getKeyCombo(e) {
        const parts = [];

        if (e.ctrlKey) parts.push('ctrl');
        if (e.shiftKey) parts.push('shift');
        if (e.altKey) parts.push('alt');

        const key = e.key.toLowerCase();
        if (!['control', 'shift', 'alt'].includes(key)) {
            parts.push(key);
        }

        return parts.join('+');
    }

    navigate(url) {
        window.location.href = url;
    }

    closeModals() {
        // 关闭所有打开的模态框
        document.querySelectorAll('.modal, .dropdown-content').forEach(el => {
            el.style.display = 'none';
        });
    }

    toggleKeyboardHints() {
        const hint = document.getElementById('keyboardHint');
        if (hint) {
            hint.classList.toggle('show');
        }
    }

    toggleTheme() {
        if (window.toggleTheme) {
            window.toggleTheme();
        }
    }
}

// 初始化快捷键
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new KeyboardShortcuts();
    });
} else {
    new KeyboardShortcuts();
}
