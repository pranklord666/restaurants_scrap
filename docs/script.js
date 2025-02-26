document.addEventListener("DOMContentLoaded", function () {
    const articlesDiv = document.getElementById("articles");
    const summariesDiv = document.getElementById("summaries");
    const summaryText = document.getElementById("summaryText");
    const loadingIndicator = document.createElement("div"); // For loading animation
    loadingIndicator.id = "loading";
    loadingIndicator.style.textAlign = "center";
    loadingIndicator.style.marginTop = "20px";
    loadingIndicator.innerHTML = '<div class="spinner"></div><p>Loading summaries...</p>';
    const backendUrl = "https://restaurants-scrap.onrender.com/api";

    // Add spinner CSS
    const spinnerStyle = document.createElement("style");
    spinnerStyle.textContent = `
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #28a745;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(spinnerStyle);

    articlesDiv.innerHTML = "<p>Loading articles...</p>";

    fetch(`${backendUrl}/articles`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
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
            articlesDiv.innerHTML = `<p class='error'>Error loading articles: ${error.message}. Check console for details.</p>`;
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
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            alert("Selection saved!");
            // Show loading animation
            summariesDiv.style.display = "block";
            summariesDiv.innerHTML = "";
            summariesDiv.appendChild(loadingIndicator);

            // Fetch and display summaries
            fetch(`${backendUrl}/results`)
                .then(resp => {
                    if (!resp.ok) throw new Error(`HTTP error! status: ${resp.status}`);
                    return resp.json();
                })
                .then(results => {
                    loadingIndicator.remove(); // Remove loading animation
                    let summaryTextContent = "";
                    results.forEach(result => {
                        summaryTextContent += `Title: ${result.title}\nSummary: ${result.summary}\n\n`; // Format for copy-paste
                    });
                    summaryText.textContent = summaryTextContent.trim(); // Set the text in the pre element
                })
                .catch(err => {
                    console.error("Error loading results:", err);
                    loadingIndicator.remove(); // Remove loading animation on error
                    summariesDiv.innerHTML = `<p class='error'>Failed to load summaries: ${err.message}. Please try again later.</p>`;
                    alert(`Failed to load summaries: ${err.message}. Please try again later.`);
                });
        })
        .catch(error => {
            console.error("Error submitting selection:", error);
            alert(`Failed to submit selection: ${error.message}. Please try again later.`);
        });
    });
});
