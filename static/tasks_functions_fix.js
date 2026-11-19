// 下载关键帧
async function downloadFrames(taskId, videoName) {
    try {
        showToast('正在打包关键帧...', 'info');

        const token = localStorage.getItem('token');
        const response = await fetch(`/api/tasks/${taskId}/download-frames`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${videoName}_frames.zip`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            showToast('关键帧下载成功！', 'success');
        } else {
            const error = await response.json();
            showToast(error.detail || '下载失败', 'error');
        }
    } catch (error) {
        console.error('下载关键帧失败:', error);
        showToast('下载失败，请稍后重试', 'error');
    }
}

// 显示字幕导出菜单
function showSubtitleMenu(event, taskId, videoName) {
    event.stopPropagation();

    const menu = document.createElement('div');
    menu.className = 'dropdown-content';
    menu.style.cssText = `
                position: absolute;
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                padding: 8px 0;
                z-index: 1000;
                min-width: 120px;
            `;

    const formats = [
        { name: 'SRT格式', value: 'srt' },
        { name: 'VTT格式', value: 'vtt' },
        { name: 'TXT格式', value: 'txt' }
    ];

    formats.forEach(format => {
        const item = document.createElement('div');
        item.textContent = format.name;
        item.style.cssText = 'padding: 10px 20px; cursor: pointer; transition: background 0.2s;';
        item.onmouseover = () => item.style.background = '#f5f5f5';
        item.onmouseout = () => item.style.background = 'white';
        item.onclick = () => {
            exportSubtitles(taskId, format.value, videoName);
            document.body.removeChild(menu);
        };
        menu.appendChild(item);
    });

    const rect = event.target.getBoundingClientRect();
    menu.style.left = rect.left + 'px';
    menu.style.top = (rect.bottom + 5) + 'px';

    document.body.appendChild(menu);

    setTimeout(() => {
        const closeMenu = (e) => {
            if (!menu.contains(e.target)) {
                document.body.removeChild(menu);
                document.removeEventListener('click', closeMenu);
            }
        };
        document.addEventListener('click', closeMenu);
    }, 100);
}

// 导出字幕
async function exportSubtitles(taskId, format, videoName) {
    try {
        showToast(`正在导出${format.toUpperCase()}字幕...`, 'info');

        const token = localStorage.getItem('token');
        const response = await fetch(`/api/tasks/${taskId}/export-subtitles?format=${format}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${videoName}_subtitles.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            showToast(`${format.toUpperCase()}字幕导出成功！`, 'success');
        } else {
            const error = await response.json();
            showToast(error.detail || '导出失败', 'error');
        }
    } catch (error) {
        console.error('导出字幕失败:', error);
        showToast('导出失败，请稍后重试', 'error');
    }
}
