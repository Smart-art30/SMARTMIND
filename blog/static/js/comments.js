document.addEventListener("DOMContentLoaded", function () {

    /* ============================================================
       HELPERS
    ============================================================ */

    const getCookie = (name) => {
        const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
        return m ? m.pop() : '';
    };
    const csrftoken = getCookie('csrftoken');

    const emojiMap = {
        like: '👍', love: '❤️', haha: '😂', wow: '😮',
        sad: '😢', angry: '😡', celebrate: '🎉'
    };

    /* ============================================================
       1. COMMENT LIKE — delegated
    ============================================================ */
    document.addEventListener('click', async (e) => {
        const btn = e.target.closest('.comment-like-btn');
        if (!btn) return;

        const res = await fetch(btn.dataset.url, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
        });
        const data = await res.json();
        if (data.success) {
            btn.classList.toggle('active', data.is_liked);
            const c = btn.querySelector('.like-count');
            if (c) c.textContent = data.likes_count;
        }
    });

    /* ============================================================
       2. REACTION MENU OPEN / CLOSE — delegated
    ============================================================ */
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.reaction-toggle-btn');
        if (btn) {
            e.stopPropagation();
            const menu = btn.parentElement.querySelector('.reaction-menu');
            document.querySelectorAll('.reaction-menu').forEach(m => {
                if (m !== menu) m.classList.add('d-none');
            });
            menu.classList.toggle('d-none');
            return;
        }

        if (!e.target.closest('.reaction-menu')) {
            document.querySelectorAll('.reaction-menu').forEach(m => m.classList.add('d-none'));
        }
    });

    /* ============================================================
       3. COMMENT REACTIONS — delegated
    ============================================================ */
    document.addEventListener('click', async (e) => {
        const btn = e.target.closest('.reaction-option:not(.post-reaction-option)');
        if (!btn) return;
        e.stopPropagation();

        const fd = new FormData();
        fd.append('reaction', btn.dataset.reaction);

        const res = await fetch(btn.dataset.url, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            body: fd,
        });
        const data = await res.json();
        if (!data.success) return;

        const container = btn.closest('.comment-item');
        const toggleBtn = container.querySelector('.reaction-toggle-btn');
        toggleBtn.querySelector('.reaction-total').textContent = data.total_reactions;
        toggleBtn.childNodes[0].nodeValue =
            data.user_reaction ? emojiMap[data.user_reaction] : '😊';

        container.querySelectorAll('.reaction-option').forEach(o => {
            o.classList.toggle('selected', o.dataset.reaction === data.user_reaction);
        });

        const summary = container.querySelector('.reaction-summary');
        if (summary) {
            summary.innerHTML = Object.entries(data.reaction_counts)
                .map(([k, v]) => `<span class="badge bg-light text-dark">${emojiMap[k] || k} ${v}</span>`)
                .join(' ');
        }

        container.querySelector('.reaction-menu').classList.add('d-none');
    });

    /* ============================================================
       4. POST REACTIONS
    ============================================================ */
    document.querySelectorAll('.post-reaction-option').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();

            const fd = new FormData();
            fd.append('reaction', btn.dataset.reaction);

            const res = await fetch(btn.dataset.url, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken },
                body: fd,
            });
            const data = await res.json();
            if (!data.success) return;

            const container = btn.closest('.post-reactions');
            const toggleBtn = container.querySelector('.reaction-toggle-btn');
            toggleBtn.querySelector('.reaction-total').textContent = data.total_reactions;
            toggleBtn.childNodes[0].nodeValue =
                data.user_reaction ? emojiMap[data.user_reaction] : '😊';

            container.querySelectorAll('.reaction-option').forEach(o => {
                o.classList.toggle('selected', o.dataset.reaction === data.user_reaction);
            });

            const summary = container.querySelector('.reaction-summary');
            if (summary) {
                summary.innerHTML = Object.entries(data.reaction_counts)
                    .map(([k, v]) => `<span class="badge bg-light text-dark">${emojiMap[k] || k} ${v}</span>`)
                    .join(' ');
            }

            container.querySelector('.reaction-menu').classList.add('d-none');
        });
    });

    /* ============================================================
       5. REPLY FORM TOGGLE — delegated
    ============================================================ */
    document.addEventListener('click', (e) => {
        const toggle = e.target.closest('.reply-toggle-btn');
        if (toggle) {
            const container = document.getElementById('comment-' + toggle.dataset.commentId);
            if (!container) return;
            const form = container.querySelector('.reply-form');
            if (!form) return;
            form.classList.toggle('d-none');
            if (!form.classList.contains('d-none')) {
                const textarea = form.querySelector('textarea');
                if (textarea) textarea.focus();
            }
            return;
        }

        const cancel = e.target.closest('.reply-cancel-btn');
        if (cancel) {
            const container = document.getElementById('comment-' + cancel.dataset.commentId);
            if (!container) return;
            const form = container.querySelector('.reply-form');
            if (form) form.classList.add('d-none');
        }
    });

    /* ============================================================
       6. "VIEW N REPLIES" TOGGLE — delegated
    ============================================================ */
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.view-replies-btn');
        if (!btn) return;

        const target = document.getElementById(btn.dataset.target);
        if (!target) return;

        const isExpanded = btn.classList.toggle('expanded');
        target.classList.toggle('collapsed', !isExpanded);

        const label = btn.querySelector('.reply-label');
        const count = target.querySelectorAll(':scope > .comment-item').length;

        if (isExpanded) {
            if (label) label.textContent = 'Hide replies';
            btn.setAttribute('aria-expanded', 'true');
        } else {
            if (label) label.textContent = `View ${count} repl${count === 1 ? 'y' : 'ies'}`;
            btn.setAttribute('aria-expanded', 'false');
        }
    });

    /* ============================================================
       7. AJAX SUBMIT — NEW TOP-LEVEL COMMENT
    ============================================================ */
    const commentForm = document.getElementById('comment-form');

    if (commentForm) {
        commentForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const submitBtn = commentForm.querySelector('button[type="submit"]');
            const originalHTML = submitBtn ? submitBtn.innerHTML : '';

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Posting…';
            }

            try {
                const res = await fetch(commentForm.action, {
                    method: 'POST',
                    body: new FormData(commentForm),
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                });
                const data = await res.json();

                if (!data.success) {
                    alert('Could not post comment.');
                    return;
                }

                const empty = document.getElementById('noCommentsBlock');
                if (empty) empty.remove();

                const list = document.getElementById('commentList');
                if (list) {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'comment-row-wrap';
                    wrapper.innerHTML = data.html;
                    list.prepend(wrapper);
                    wrapper.classList.add('comment-revealing');
                    setTimeout(() => wrapper.classList.remove('comment-revealing'), 350);
                }

                commentForm.querySelector('textarea').value = '';

                document.querySelectorAll('.comments-count-display').forEach(el => {
                    el.textContent = data.comments_count;
                });
            } catch (err) {
                console.error(err);
                alert('Network error. Please try again.');
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalHTML;
                }
            }
        });
    }

    /* ============================================================
       8. AJAX SUBMIT — REPLY — delegated
    ============================================================ */
    document.addEventListener('submit', async (e) => {
        const form = e.target.closest('.reply-form');
        if (!form) return;
        e.preventDefault();

        const submitBtn = form.querySelector('.reply-submit-btn');
        const originalText = submitBtn ? submitBtn.textContent : '';

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Posting…';
        }

        try {
            const res = await fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            const data = await res.json();

            if (!data.success) {
                alert('Could not post reply.');
                return;
            }

            const parent = document.getElementById('comment-' + data.parent_id);
            if (!parent) return;

            let repliesWrap = parent.querySelector(':scope > .comment-replies');
            let toggleBtn = parent.querySelector(':scope > .view-replies-btn');

            if (!repliesWrap) {
                repliesWrap = document.createElement('div');
                repliesWrap.className = 'comment-replies';
                repliesWrap.id = 'replies-' + data.parent_id;
                parent.appendChild(repliesWrap);
            }

            if (!toggleBtn) {
                toggleBtn = document.createElement('button');
                toggleBtn.type = 'button';
                toggleBtn.className = 'view-replies-btn expanded';
                toggleBtn.dataset.target = 'replies-' + data.parent_id;
                toggleBtn.setAttribute('aria-expanded', 'true');
                toggleBtn.innerHTML =
                    '<span class="reply-caret"></span>' +
                    '<span class="reply-label">Hide replies</span>';
                parent.insertBefore(toggleBtn, repliesWrap);
            } else {
                repliesWrap.classList.remove('collapsed');
                toggleBtn.classList.add('expanded');
                const lbl = toggleBtn.querySelector('.reply-label');
                if (lbl) lbl.textContent = 'Hide replies';
            }

            const wrapper = document.createElement('div');
            wrapper.innerHTML = data.html;
            const newNode = wrapper.firstElementChild;
            repliesWrap.appendChild(newNode);
            newNode.classList.add('comment-revealing');
            setTimeout(() => newNode.classList.remove('comment-revealing'), 350);

            form.querySelector('textarea').value = '';
            form.classList.add('d-none');

            document.querySelectorAll('.comments-count-display').forEach(el => {
                const n = parseInt(el.textContent || '0', 10);
                el.textContent = n + 1;
            });

        } catch (err) {
            console.error(err);
            alert('Network error. Please try again.');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        }
    });

    /* ============================================================
       9. COMMENT EDIT — open the inline edit form
    ============================================================ */
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.comment-edit-btn');
        if (!btn) return;

        const container = document.getElementById('comment-' + btn.dataset.commentId);
        if (!container) return;

        const form = container.querySelector('.comment-edit-form');
        if (!form) return;

        // Hide any other open edit forms
        document.querySelectorAll('.comment-edit-form').forEach(f => {
            if (f !== form) f.classList.add('d-none');
        });

        form.classList.remove('d-none');

        const textarea = form.querySelector('textarea');
        if (textarea) {
            textarea.focus();
            // Place cursor at end
            textarea.setSelectionRange(textarea.value.length, textarea.value.length);
        }
    });

    /* Cancel edit */
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.comment-cancel-edit-btn');
        if (!btn) return;

        const container = document.getElementById('comment-' + btn.dataset.commentId);
        if (!container) return;

        const form = container.querySelector('.comment-edit-form');
        if (form) form.classList.add('d-none');
    });

    /* ============================================================
       10. COMMENT EDIT — save changes
    ============================================================ */
    document.addEventListener('submit', async (e) => {
        const form = e.target.closest('.comment-edit-form');
        if (!form) return;
        e.preventDefault();

        const saveBtn = form.querySelector('.comment-save-btn');
        const originalText = saveBtn ? saveBtn.textContent : '';

        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.textContent = 'Saving…';
        }

        try {
            const res = await fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            const data = await res.json();

            if (!data.success) {
                alert(data.message || 'Could not save changes.');
                return;
            }

            const container = document.getElementById('comment-' + data.comment_id);
            if (!container) return;

            // Update the visible body
            const body = container.querySelector(':scope > .comment-body');
            if (body) body.innerHTML = data.text;

            // Add the "· edited" tag if not present
            const header = container.querySelector(':scope > .comment-header');
            if (header && !header.querySelector('.comment-edited-tag')) {
                header.appendChild(document.createTextNode(' '));
                const tag = document.createElement('small');
                tag.className = 'text-muted comment-edited-tag';
                tag.textContent = '· edited';
                header.appendChild(tag);
            }

            // Hide the form
            form.classList.add('d-none');
        } catch (err) {
            console.error(err);
            alert('Network error. Please try again.');
        } finally {
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = originalText;
            }
        }
    });

    /* ============================================================
       11. COMMENT DELETE — delegated
    ============================================================ */
    document.addEventListener('click', async (e) => {
        const btn = e.target.closest('.comment-delete-btn');
        if (!btn) return;

        if (!confirm('Delete this comment? This cannot be undone.')) return;

        try {
            const res = await fetch(btn.dataset.url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'X-Requested-With': 'XMLHttpRequest',
                },
            });
            const data = await res.json();

            if (!data.success) {
                alert(data.message || 'Could not delete comment.');
                return;
            }

            // Remove the comment (or its top-level wrapper) from the DOM
            const container = document.getElementById('comment-' + btn.dataset.commentId);
            if (container) {
                const wrapper = container.closest('.comment-row-wrap');
                const nodeToRemove = wrapper || container;

                nodeToRemove.style.transition = 'opacity .2s, transform .2s';
                nodeToRemove.style.opacity = '0';
                nodeToRemove.style.transform = 'translateY(-6px)';

                setTimeout(() => nodeToRemove.remove(), 220);
            }

            // Update every comment count display on the page
            document.querySelectorAll('.comments-count-display').forEach(el => {
                el.textContent = data.comments_count;
            });
        } catch (err) {
            console.error(err);
            alert('Network error. Please try again.');
        }
    });

});