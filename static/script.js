function processScenario() {

    const scenarioText = document.getElementById("scenario").value;

    //sends request HTTP POST (to server) from froentend to backend
    fetch('/process_scenario', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: scenarioText })
    })

    .then(response => response.json())

    .then(data => {
        // Display the Entities
        const entitiesList = document.getElementById("entities-list");
        entitiesList.innerHTML = ""; // Clear existing list
        for (const entity in data.entities) {
            const entityElement = document.createElement("div");
            entityElement.innerHTML = `<strong>${entity}</strong>: ${data.entities[entity].join(", ")}`;
            entitiesList.appendChild(entityElement);
        }

        // Display the Relationships
        const relationshipsList = document.getElementById("relationships-list");
        relationshipsList.innerHTML = ""; // Clear existing list
        data.relationships.forEach(rel => {
            const relElement = document.createElement("div");
            relElement.innerHTML = `${rel[0]} -[${rel[1]}]-> ${rel[2]}`;
            relationshipsList.appendChild(relElement);
        });

        // Display the ERD Image
        const erdImage = document.getElementById("erd-image");
        const uniqueErdImagePath = `/static/erd_images/${data.erd_image_path}?v=${Date.now()}`; // Add unique query parameter
        erdImage.src = uniqueErdImagePath;
        erdImage.style.display = 'block';

        // Display the SQL Statements
        const sqlStatementsDiv = document.getElementById("sql-statements");
        sqlStatementsDiv.innerHTML = ""; // Clear existing content
        if (Array.isArray(data.sql_statements)) {
            const preElement = document.createElement("pre");
            preElement.style.whiteSpace = "pre-wrap"; // Wrap long lines
            preElement.style.background = "#f4f4f4";
            preElement.style.padding = "10px";
            preElement.style.border = "1px solid #ddd";
            preElement.style.borderRadius = "5px";
            preElement.style.overflowX = "auto";

            // Join statements with a newline for better readability
            preElement.innerHTML = data.sql_statements.join("\n\n");
            sqlStatementsDiv.appendChild(preElement);
        } else {
            sqlStatementsDiv.textContent = "No SQL statements generated.";
        }
    })
    .catch(error => console.error('Error:', error));
}
