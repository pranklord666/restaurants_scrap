document.addEventListener("DOMContentLoaded", function () {
    const articlesDiv = document.getElementById("articles");

    // Fetch articles from Render backend
    fetch("https://your-render-backend.com/articles")  // Replace with your actual Render backend URL
        .then(response => response.json())
        .then(data => {
            data.forEach(article => {
                articlesDiv.innerHTML += `
                    <label>
                        <input type="checkbox" name="selected_articles" value="${article.id}">
                        ${article.title}
                    </label><br>
                `;
            });
        })
        .catch(error => console.error("Error loading articles:", error));

    // Handle form submission
    document.getElementById("articleForm").addEventListener("submit", function (event) {
        event.preventDefault();

        let selected = [];
        document.querySelectorAll('input[name="selected_articles"]:checked').forEach(input => {
            selected.push(input.value);
        });

        fetch("https://your-render-backend.com/submit", {  // Replace with your actual Render backend URL
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ selected_articles: selected })
        })
        .then(response => response.json())
        .then(() => {
            window.location.href = "results.html";  // Redirect to results page
        })
        .catch(error => console.error("Error submitting selection:", error));
    });
});
