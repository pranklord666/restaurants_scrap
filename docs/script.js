document.addEventListener("DOMContentLoaded", function () {
    const articlesDiv = document.getElementById("articles");
    const backendUrl = "https://restaurants-scrap.onrender.com";

    articlesDiv.innerHTML = "<p>Loading articles...</p>";

    fetch(`${backendUrl}/articles`)
        .then(response => {
            if (!response.ok) throw new Error("Network response was not ok");
            return response.json();
        })
        .then(data => {
            articlesDiv.innerHTML = "";

            if (data.length === 0) {
                articlesDiv.innerHTML = "<p class='error'>No articles found. Try again later.</p>";
                return;
            }

            data.forEach(article => {
                articlesDiv.innerHTML += `
                    <label>
                        <input type="radio" name="article_${article.id}" value="in"> In
                        <input type="radio" name="article_${article.id}" value="out"> Out
                        ${article.title}
                    </label><br>
                `;
            });
        })
        .catch(error => {
            console.error("Error loading articles:", error);
            articlesDiv.innerHTML = "<p class='error'>Error loading articles. Check console for details.</p>";
        });

    // Handle form submission
    document.getElementById("articleForm").addEventListener("submit", function (event) {
        event.preventDefault();

        const selections = {};
        document.querySelectorAll("input[type=radio]:checked").forEach(input => {
            const articleId = input.name.split("_")[1];
            selections[articleId] = input.value;
        });

        fetch(`${backendUrl}/update-selection`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(selections)
        })
        .then(response => {
            if (!response.ok) throw new Error("Failed to submit selection");
            return response.json();
        })
        .then(data => alert("Selection saved!"))
        .catch(error => console.error("Error submitting selection:", error));
    });
});
