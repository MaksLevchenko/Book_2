// Динамически открывать форму "Ответить" под нужным комментарием
// Требует, чтобы у кнопки "Ответить" была data-comment-id и ближайший родитель-ли к комменту

document.addEventListener("DOMContentLoaded", function () {
  document.body.addEventListener("click", function (e) {
    if (e.target.classList.contains("reply-btn")) {
      e.preventDefault();
      // Найти ближайший .grid (блок с кнопками этого комментария)
      const grid = e.target.closest(".grid");
      if (!grid) return;
      
      // Если уже есть открытая reply-form — удалить ее
      const existing = grid.querySelector(".reply-form");
      if (existing) {
        existing.remove();
        return;
      }
      // Получаем id комментария
      const commentBlock = e.target.closest("li");
      const parentId = commentBlock ? commentBlock.getAttribute('data-comment-id') : '';
      // Теперь parentId гарантированно - id комментария, к которому будет ответ.

      // Найти CSRF-токен из любой формы на этой странице
      const csrf = document.querySelector('input[name="csrfmiddlewaretoken"]');
      const csrfToken = csrf ? csrf.value : '';
      // Получить data-add-comment-url из li
      const addCommentUrl = commentBlock ? commentBlock.getAttribute('data-add-comment-url') : '';
      // Собираем HTML формы
      const form = document.createElement("form");
      form.className = "reply-form";
      form.method = "post";
      form.setAttribute("action", addCommentUrl);
      form.setAttribute("hx-post", addCommentUrl); // для HTMX
      form.setAttribute("hx-target", "#comments");
      form.setAttribute("hx-swap", "outerHTML");
      form.setAttribute("hx-on::after-request", "this.reset()");
      form.innerHTML = `
        <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
        <input type="hidden" name="parent_id" value="${parentId || ''}" />
        <input type="text" name="text" placeholder="Напишите ваш ответ..." required style="min-width:150px" />
        <button type="submit">Отправить</button>
      `;

      // Вставить в контейнер .reply-form-container после основного текста комментария
      const replyContainer = commentBlock.querySelector('.reply-form-container');
      if(replyContainer) {
        replyContainer.innerHTML = '';
        replyContainer.appendChild(form);
      }
    }
  });
});
